import streamlit as st
import numpy as np
from PIL import Image
import pandas as pd
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

LANG = st.sidebar.selectbox("Language", ["BG", "EN"])

t = {
    "BG": {
        "title": "🥗 AI Скенер за Съставки",
        "scan": "Сканирай",
        "text": "Разпознат текст",
        "harmful": "Вредни вещества",
        "safe": "Няма опасни вещества",
        "score": "Оценка",
        "risk": "Риск"
    },
    "EN": {
        "title": "🥗 AI Ingredient Scanner",
        "scan": "Scan",
        "text": "Detected text",
        "harmful": "Harmful ingredients",
        "safe": "No harmful ingredients",
        "score": "Score",
        "risk": "Risk"
    }
}[LANG]

# =========================================================
# FULL HARMFUL DATABASE (EXPANDED)
# =========================================================

harmful_ingredients = {
    # PRESERVATIVES
    "e200": {"name": "Sorbic Acid", "risk": "May cause irritation", "level": "low", "score": -10},
    "e202": {"name": "Potassium Sorbate", "risk": "Possible allergies", "level": "low", "score": -10},
    "e211": {"name": "Sodium Benzoate", "risk": "May form harmful compounds", "level": "medium", "score": -15},
    "e220": {"name": "Sulfur Dioxide", "risk": "Asthma trigger", "level": "high", "score": -20},
    "e250": {"name": "Sodium Nitrite", "risk": "Linked to cancer risk", "level": "high", "score": -25},

    # FLAVOR ENHANCERS
    "e621": {"name": "Monosodium Glutamate (MSG)", "risk": "May cause headaches", "level": "medium", "score": -15},
    "e627": {"name": "Disodium Guanylate", "risk": "Flavor enhancer", "level": "low", "score": -10},
    "e631": {"name": "Disodium Inosinate", "risk": "Flavor enhancer", "level": "low", "score": -10},

    # COLORANTS
    "e102": {"name": "Tartrazine", "risk": "Hyperactivity risk", "level": "high", "score": -20},
    "e110": {"name": "Sunset Yellow", "risk": "Allergic reactions", "level": "high", "score": -20},
    "e122": {"name": "Carmoisine", "risk": "May cause reactions", "level": "medium", "score": -15},
    "e124": {"name": "Ponceau 4R", "risk": "Possible allergen", "level": "medium", "score": -15},
    "e129": {"name": "Allura Red", "risk": "Hyperactivity risk", "level": "high", "score": -20},

    # SWEETENERS
    "aspartame": {"name": "Aspartame", "risk": "Controversial sweetener", "level": "high", "score": -20},
    "acesulfame": {"name": "Acesulfame K", "risk": "Artificial sweetener", "level": "medium", "score": -15},
    "saccharin": {"name": "Saccharin", "risk": "Old sweetener", "level": "low", "score": -10},

    # FATS
    "trans fat": {"name": "Trans Fat", "risk": "Heart disease risk", "level": "high", "score": -30},

    # COMMON SHORT FORM
    "msg": {"name": "Monosodium Glutamate", "risk": "Headache risk", "level": "medium", "score": -15}
}

# =========================================================
# ALLERGENS
# =========================================================

allergens = ["milk", "soy", "gluten", "nuts", "egg", "wheat"]

# =========================================================
# IMAGE PREPROCESS (NO CV2)
# =========================================================

def preprocess(image):

    img = np.array(image)

    # resize for stability
    h, w = img.shape[:2]
    if w > 1200:
        scale = 1200 / w
        new_size = (int(w * scale), int(h * scale))
        img = np.array(Image.fromarray(img).resize(new_size))

    # grayscale
    img = Image.fromarray(img).convert("L")

    return img

# =========================================================
# OCR
# =========================================================

def extract_text(image):

    try:
        img = preprocess(image)

        config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(
            img,
            lang="eng",
            config=config
        )

        text = re.sub(r'\s+', ' ', text.lower()).strip()
        return text

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

file = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
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
                st.error(f"{item['name']} | {item['risk']} | {item['level'].upper()}")
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
