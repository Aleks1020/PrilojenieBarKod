import streamlit as st
import numpy as np
from PIL import Image
import pandas as pd
import re
from datetime import datetime
import pytesseract

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
# CHECK TESSERACT
# =========================================================

def check_tesseract():
    try:
        return pytesseract.get_tesseract_version()
    except:
        return None

if not check_tesseract():
    st.error("Tesseract is not installed or not available.")
    st.stop()

# =========================================================
# LANGUAGE
# =========================================================

LANG = st.sidebar.selectbox("Language", ["BG", "EN"])

t = {
    "BG": {
        "title": "🥗 AI Скенер за Храна",
        "scan": "Сканирай",
        "text": "Текст",
        "harmful": "Вредни вещества",
        "safe": "Няма вредни вещества",
        "score": "Оценка",
        "risk": "Риск",
        "insights": "Анализ"
    },
    "EN": {
        "title": "🥗 AI Food Scanner",
        "scan": "Scan",
        "text": "Text",
        "harmful": "Harmful ingredients",
        "safe": "No harmful ingredients",
        "score": "Score",
        "risk": "Risk",
        "insights": "Insights"
    }
}[LANG]

# =========================================================
# HARMFUL INGREDIENTS
# =========================================================

harmful_ingredients = {
    "e621": {"name": "MSG", "risk": "Headache risk", "score": -15},
    "e250": {"name": "Sodium Nitrite", "risk": "Cancer risk", "score": -25},
    "aspartame": {"name": "Aspartame", "risk": "Sweetener risk", "score": -20},
    "e102": {"name": "Tartrazine", "risk": "Hyperactivity risk", "score": -20},
    "trans fat": {"name": "Trans Fat", "risk": "Heart disease risk", "score": -30}
}

# =========================================================
# ALCOHOL DETECTION (NEW)
# =========================================================

alcohol_keywords = {
    "beer": {"score": -20, "risk": "Alcohol consumption detected"},
    "wine": {"score": -25, "risk": "Alcohol consumption detected"},
    "vodka": {"score": -30, "risk": "High alcohol content"},
    "whiskey": {"score": -30, "risk": "High alcohol content"},
    "rum": {"score": -30, "risk": "High alcohol content"},
    "alcohol": {"score": -25, "risk": "Alcohol detected"},
    "ethanol": {"score": -25, "risk": "Ethanol detected"}
}

# =========================================================
# SUGAR / NUTRIENT RULES
# =========================================================

risk_rules = {
    "sugar": (0, 5, 25, "High sugar intake risk"),
    "syrup": (0, 5, 20, "High syrup content"),
    "glucose": (0, 5, 20, "Fast sugar spike"),
    "fructose": (0, 5, 20, "Metabolic sugar load")
}

# =========================================================
# ALLERGENS
# =========================================================

allergens = ["milk", "soy", "gluten", "nuts", "egg", "wheat"]

# =========================================================
# IMAGE PREPROCESS
# =========================================================

def preprocess(image):
    img = np.array(image)

    h, w = img.shape[:2]
    if w > 1200:
        scale = 1200 / w
        img = np.array(Image.fromarray(img).resize((int(w * scale), int(h * scale))))

    return Image.fromarray(img).convert("L")

# =========================================================
# OCR
# =========================================================

def extract_text(image):
    try:
        img = preprocess(image)

        text = pytesseract.image_to_string(
            img,
            lang="eng",
            config="--oem 3 --psm 6"
        )

        return re.sub(r"\s+", " ", text.lower()).strip()

    except Exception as e:
        st.error(f"OCR error: {e}")
        return ""

# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze(text):

    score = 100
    found = []
    insights = []

    # E-numbers / harmful
    for k, v in harmful_ingredients.items():
        if k in text:
            found.append(v)
            score += v["score"]
            insights.append(f"{v['name']}: {v['risk']}")

    # ALCOHOL detection
    for k, v in alcohol_keywords.items():
        if k in text:
            found.append({"name": k, "risk": v["risk"]})
            score += v["score"]
            insights.append(v["risk"])

    # SUGAR / nutrients
    for k, (low, med, high_penalty, msg) in risk_rules.items():
        if k in text:
            if k == "sugar":
                # rough estimation if number exists
                match = re.search(r"sugar[^0-9]*([0-9]+)", text)
                if match:
                    val = int(match.group(1))
                    if val > 25:
                        score -= 25
                        insights.append("High sugar (>25g) detected")
                    elif val > 10:
                        score -= 15
                        insights.append("Medium sugar detected")
                    else:
                        insights.append("Low sugar detected")
                else:
                    score -= 10
                    insights.append("Sugar detected (unknown amount)")
            else:
                score -= high_penalty
                insights.append(msg)

    return found, max(0, min(100, score)), insights

# =========================================================
# ALLERGENS
# =========================================================

def detect_allergens(text):
    return list({a for a in allergens if a in text})

# =========================================================
# RISK
# =========================================================

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

        with st.spinner("Analyzing..."):

            text = extract_text(img)
            found, score, insights = analyze(text)
            allergens_found = detect_allergens(text)
            risk = risk_label(score)

        # TEXT
        st.subheader(t["text"])
        st.text_area("", text, height=150)

        # SCORE
        st.subheader(t["score"])
        st.progress(score / 100)
        st.metric(t["risk"], risk)

        # INSIGHTS
        st.subheader(t["insights"])
        for i in insights:
            st.info(i)

        # HARMFUL
        st.subheader(t["harmful"])
        if found:
            for item in found:
                st.warning(f"{item['name']} | {item['risk']}")
        else:
            st.success(t["safe"])

        # ALLERGENS
        if allergens_found:
            st.warning("Allergens: " + ", ".join(allergens_found))

        # HISTORY
        st.session_state.history.append({
            "time": datetime.now(),
            "score": score,
            "risk": risk
        })

        st.dataframe(pd.DataFrame(st.session_state.history))
