import streamlit as st
import numpy as np
from PIL import Image
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Food Scanner",
    page_icon="🥗",
    layout="centered"
)

if "history" not in st.session_state:
    st.session_state.history = []

# =========================================================
# LAZY OCR (IMPORTANT FIX)
# =========================================================

@st.cache_resource
def get_reader():
    import easyocr
    return easyocr.Reader(['bg', 'en'], gpu=False)

# =========================================================
# 🔥 FULL HARMFUL INGREDIENT DATABASE (RESTORED + EXPANDED)
# =========================================================

INGREDIENTS = {
    # ================= E-NUMBERS =================
    "e102": [
        "e102", "tartrazine", "тартразин", "yellow 5", "food coloring", "оцветител жълто"
    ],
    "e104": [
        "e104", "quinoline yellow", "жълт оцветител"
    ],
    "e110": [
        "e110", "sunset yellow", "оранжев оцветител"
    ],
    "e124": [
        "e124", "ponceau 4r", "червен оцветител"
    ],
    "e129": [
        "e129", "allura red", "червено 40"
    ],

    "e211": [
        "e211", "sodium benzoate", "натриев бензоат", "preservative"
    ],
    "e202": [
        "e202", "potassium sorbate", "калиев сорбат"
    ],
    "e220": [
        "e220", "sulphites", "сулфити"
    ],

    "e250": [
        "e250", "sodium nitrite", "нитрит", "консервант за месо"
    ],

    "e407": [
        "e407", "carrageenan", "карагенан"
    ],

    "e621": [
        "e621", "msg", "monosodium glutamate", "мононатриев глутамат"
    ],

    # ================= SUGAR FAMILY =================
    "sugar": [
        "sugar", "захар", "glucose", "глюкоза",
        "fructose", "фруктоза", "dextrose",
        "corn syrup", "glucose syrup",
        "syrup", "сироп", "maltose"
    ],

    # ================= ALCOHOL / BEER =================
    "alcohol": [
        "alcohol", "ethanol", "beer", "wine",
        "бира", "вино", "ракия", "уиски",
        "хмел", "малц", "fermentation"
    ],

    # ================= ADDITIVES =================
    "additives": [
        "flavor", "aroma", "aroma", "консервант",
        "coloring", "stabilizer", "emulsifier"
    ],

    # ================= FATS =================
    "fat": [
        "fat", "oil", "hydrogenated", "мазнини", "масло"
    ],

    # ================= CARBS =================
    "carbs": [
        "carbohydrate", "carbs", "въглехидрат"
    ]
}

# =========================================================
# SCORES
# =========================================================

SCORES = {
    "e102": -20, "e104": -20, "e110": -20,
    "e124": -25, "e129": -25,

    "e211": -15, "e202": -10, "e220": -15,
    "e250": -30,

    "e407": -20,
    "e621": -20,

    "sugar": -10,
    "alcohol": -20,
    "additives": -10,
    "fat": -10,
    "carbs": -10
}

# =========================================================
# OCR FUNCTION
# =========================================================

def extract_text(image):

    reader = get_reader()

    img = np.array(image)

    results = reader.readtext(img)

    words = []

    for bbox, text, conf in results:
        if conf > 0.4:
            words.append(text.lower())

    return " ".join(words)

# =========================================================
# ANALYSIS ENGINE (IMPROVED MATCHING)
# =========================================================

def analyze(text):

    score = 100
    found = []

    for key, words in INGREDIENTS.items():

        for w in words:
            if w in text:
                score += SCORES[key]
                found.append(f"{key.upper()} → {w}")
                break

    score = max(0, min(100, score))

    return score, found

# =========================================================
# RISK
# =========================================================

def risk(score):
    if score >= 75:
        return "LOW"
    elif score >= 45:
        return "MEDIUM"
    return "HIGH"

# =========================================================
# UI
# =========================================================

st.title("🥗 AI Food Scanner")

file = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
cam = st.camera_input("Camera")

img = None

if file:
    img = Image.open(file)
elif cam:
    img = Image.open(cam)

# =========================================================
# MAIN
# =========================================================

if img:

    st.image(img, use_container_width=True)

    if st.button("Scan", type="primary"):

        try:

            text = extract_text(img)
            score, found = analyze(text)

            st.subheader("Detected text")
            st.text_area("", text, height=150)

            st.subheader("Score")
            st.progress(score / 100)
            st.write("Risk:", risk(score))

            st.subheader("Detected harmful ingredients")

            if found:
                for f in found:
                    st.warning(f)
            else:
                st.success("Clean")

            st.session_state.history.append({
                "time": datetime.now(),
                "score": score,
                "risk": risk(score)
            })

            st.subheader("History")
            st.dataframe(st.session_state.history)

        except Exception as e:
            st.error(f"OCR error: {e}")
