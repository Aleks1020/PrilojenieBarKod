import streamlit as st
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
import re

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Food Scanner",
    page_icon="🥗",
    layout="centered"
)

# =========================================================
# SESSION HISTORY
# =========================================================

if "history" not in st.session_state:
    st.session_state.history = []

# =========================================================
# OCR (EasyOCR)
# =========================================================

@st.cache_resource
def load_reader():
    return easyocr.Reader(['bg', 'en'], gpu=False)

reader = load_reader()

# =========================================================
# TRANSLATIONS
# =========================================================

T = {
    "bg": {
        "title": "🥗 AI Скенер за Храни",
        "scan": "Сканирай",
        "text": "Текст",
        "score": "Оценка",
        "risk": "Риск",
        "harmful": "Вредни съставки"
    },
    "en": {
        "title": "🥗 AI Food Scanner",
        "scan": "Scan",
        "text": "Text",
        "score": "Score",
        "risk": "Risk",
        "harmful": "Harmful ingredients"
    }
}

lang = st.sidebar.selectbox("Language", ["bg", "en"])
t = T[lang]

# =========================================================
# 🔥 INGREDIENT DATABASE (EXPANDED + CLEAN)
# =========================================================

INGREDIENTS = {
    # ================= E NUMBERS =================
    "e102": {
        "names": ["e102", "tartrazine", "тартразин", "yellow 5", "food coloring"],
        "score": -20
    },
    "e110": {
        "names": ["e110", "sunset yellow", "orange yellow", "оцветител"],
        "score": -20
    },
    "e211": {
        "names": ["e211", "sodium benzoate", "натриев бензоат", "preservative"],
        "score": -15
    },
    "e250": {
        "names": ["e250", "sodium nitrite", "нитрит", "nitrite"],
        "score": -30
    },
    "e407": {
        "names": ["e407", "carrageenan", "карагенан"],
        "score": -20
    },

    # ================= SUGAR =================
    "sugar": {
        "names": [
            "sugar", "захар", "glucose", "глюкоза",
            "fructose", "фруктоза", "syrup", "сироп",
            "corn syrup", "dextrose", "maltose"
        ],
        "score": -10
    },

    # ================= ALCOHOL =================
    "alcohol": {
        "names": [
            "alcohol", "ethanol", "beer", "wine",
            "бира", "вино", "малц", "хмел"
        ],
        "score": -20
    },

    # ================= ADDITIVES =================
    "additives": {
        "names": [
            "flavor", "aroma", "preservative",
            "консервант", "аромат", "coloring"
        ],
        "score": -10
    }
}

# =========================================================
# OCR FUNCTION (STABLE)
# =========================================================

def extract_text(image):

    img = np.array(image)

    results = reader.readtext(img)

    text_parts = []

    for bbox, text, conf in results:
        if conf > 0.4:   # 🔥 важен филтър
            text_parts.append(text.lower())

    return " ".join(text_parts)

# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze(text):

    score = 100
    found = []

    for key, item in INGREDIENTS.items():
        for name in item["names"]:
            if name in text:
                score += item["score"]
                found.append(f"{key} → {name}")
                break

    score = max(0, min(100, score))

    return score, found

# =========================================================
# RISK LEVEL
# =========================================================

def risk_level(score):
    if score >= 75:
        return "LOW"
    elif score >= 45:
        return "MEDIUM"
    return "HIGH"

# =========================================================
# UI
# =========================================================

st.title(t["title"])

file = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
cam = st.camera_input("Camera")

img = None

if file:
    img = Image.open(file)
elif cam:
    img = Image.open(cam)

# =========================================================
# MAIN LOGIC
# =========================================================

if img:

    st.image(img, use_container_width=True)

    if st.button(t["scan"], type="primary"):

        text = extract_text(img)
        score, found = analyze(text)

        # TEXT
        st.subheader(t["text"])
        st.text_area("", text, height=150)

        # SCORE
        st.subheader(t["score"])
        st.progress(score / 100)
        st.write(f"{t['risk']}: {risk_level(score)}")

        # FOUND
        st.subheader(t["harmful"])

        if found:
            for f in found:
                st.warning(f)
        else:
            st.success("Clean")

        # HISTORY
        st.session_state.history.append({
            "time": datetime.now(),
            "score": score,
            "risk": risk_level(score)
        })

        st.subheader("History")
        st.dataframe(st.session_state.history)
