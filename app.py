import streamlit as st
import numpy as np
from PIL import Image
import pandas as pd
import cv2
import re
from datetime import datetime
import pytesseract
import warnings

warnings.filterwarnings("ignore")

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Food Ingredient Scanner",
    page_icon="🥗",
    layout="centered"
)

if "history" not in st.session_state:
    st.session_state.history = []

# =========================================================
# LANGUAGE
# =========================================================

LANGUAGES = {"BG": "bg", "EN": "en"}
lang = st.sidebar.selectbox("Language", list(LANGUAGES.keys()))
LANG = LANGUAGES[lang]

t = {
    "bg": {
        "title": "🥗 AI Скенер за Хранителни Съставки",
        "scan": "Сканирай",
        "text": "Текст",
        "harmful": "Вредни вещества",
        "safe": "Няма опасни вещества",
        "score": "Оценка",
        "risk": "Риск"
    },
    "en": {
        "title": "🥗 AI Food Scanner",
        "scan": "Scan",
        "text": "Text",
        "harmful": "Harmful ingredients",
        "safe": "No harmful ingredients",
        "score": "Score",
        "risk": "Risk"
    }
}[LANG]

# =========================================================
# EXTENDED HARMFUL DATABASE (BIG E-NUMBER SET)
# =========================================================

harmful_ingredients = {

    # ===== PRESERVATIVES =====
    "e200": {"name": "Sorbic Acid", "risk": "May cause irritation", "score": -10},
    "e202": {"name": "Potassium Sorbate", "risk": "Allergic reactions possible", "score": -10},
    "e211": {"name": "Sodium Benzoate", "risk": "May form benzene in acid drinks", "score": -20},
    "e220": {"name": "Sulfur Dioxide", "risk": "Asthma trigger", "score": -20},
    "e223": {"name": "Sodium Metabisulfite", "risk": "Allergen for sensitive people", "score": -20},
    "e250": {"name": "Sodium Nitrite", "risk": "Linked to cancer risk", "score": -25},

    # ===== FLAVOR ENHANCERS =====
    "e621": {"name": "MSG", "risk": "May cause headaches", "score": -15},
    "e627": {"name": "Disodium Guanylate", "risk": "Flavor enhancer", "score": -10},
    "e631": {"name": "Disodium Inosinate", "risk": "Flavor enhancer", "score": -10},

    # ===== COLORANTS =====
    "e102": {"name": "Tartrazine", "risk": "Hyperactivity in children", "score": -20},
    "e110": {"name": "Sunset Yellow", "risk": "Allergic reactions", "score": -20},
    "e122": {"name": "Carmoisine", "risk": "May cause hyperactivity", "score": -15},
    "e124": {"name": "Ponceau 4R", "risk": "Possible allergen", "score": -15},
    "e129": {"name": "Allura Red", "risk": "Hyperactivity risk", "score": -20},

    # ===== SWEETENERS =====
    "aspartame": {"name": "Aspartame", "risk": "Controversial sweetener", "score": -20},
    "acesulfame": {"name": "Acesulfame K", "risk": "Artificial sweetener", "score": -15},
    "saccharin": {"name": "Saccharin", "risk": "Old artificial sweetener", "score": -10},

    # ===== FATS =====
    "trans fat": {"name": "Trans Fat", "risk": "Heart disease risk", "score": -30},

    # ===== OTHER =====
    "msg": {"name": "Monosodium Glutamate", "risk": "Headaches possible", "score": -15}
}

# =========================================================
# ALLERGENS
# =========================================================

allergens = ["milk", "soy", "gluten", "nuts", "egg", "wheat"]

# =========================================================
# OCR (OPTIMIZED)
# =========================================================

def preprocess(image):

    img = np.array(image)

    h, w = img.shape[:2]
    if w > 1200:
        scale = 1200 / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    gray = cv2.convertScaleAbs(gray, alpha=1.3, beta=10)

    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 2
    )

def extract_text(image):

    try:
        img = preprocess(image)

        config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(
            img,
            lang="eng",
            config=config
        )

        return re.sub(r'\s+', ' ', text.lower()).strip()

    except Exception as e:
        st.error(f"OCR error: {e}")
        return ""

# =========================================================
# ANALYSIS
# =========================================================

def analyze(text):

    found = []
    score = 100

    for key, data in harmful_ingredients.items():

        if key in text:
            found.append(data)
            score += data["score"]

    return found, max(0, min(100, score))

def detect_allergens(text):

    return list({a for a in allergens if a in text})

def risk_label(score):

    if score >= 75:
        return "LOW"
    elif score >= 45:
        return "MEDIUM"
    return "HIGH"

# =========================================================
# UI
# =========================================================

st.title(t["title"])

file = st.file_uploader("Upload", type=["png", "jpg", "jpeg"])
cam = st.camera_input("Camera")

img = None

if file:
    img = Image.open(file).convert("RGB")
elif cam:
    img = Image.open(cam).convert("RGB")

# =========================================================
# MAIN
# =========================================================

if img:

    st.image(img, use_container_width=True)

    if st.button(t["scan"], type="primary"):

        with st.spinner("Processing..."):

            text = extract_text(img)
            found, score = analyze(text)
            allerg = detect_allergens(text)
            risk = risk_label(score)

        # TEXT
        st.subheader(t["text"])
        st.text_area("", text, height=150)

        # SCORE
        st.subheader(t["score"])
        st.progress(score / 100)
        st.metric(t["risk"], risk)

        # HARMFUL
        st.subheader(t["harmful"])

        if found:
            for item in found:
                st.error(f"{item['name']} → {item['risk']}")
        else:
            st.success(t["safe"])

        # ALLERGENS
        if allerg:
            st.warning(", ".join(allerg))

        # HISTORY
        st.session_state.history.append({
            "time": datetime.now(),
            "score": score,
            "risk": risk
        })

        st.dataframe(pd.DataFrame(st.session_state.history))
