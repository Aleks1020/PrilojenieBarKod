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
# OCR CHECK
# =========================================================

try:
    pytesseract.get_tesseract_version()
except:
    st.error("Tesseract is not installed or not in PATH.")
    st.stop()

# =========================================================
# LANGUAGE
# =========================================================

LANG = st.sidebar.selectbox("Language", ["BG", "EN"])

T = {
    "BG": {
        "title": "🥗 AI Скенер за Храна",
        "scan": "Сканирай",
        "text": "Текст",
        "score": "Оценка",
        "risk": "Риск",
        "harmful": "Вредни съставки",
        "safe": "Няма опасни съставки",
        "insights": "Анализ"
    },
    "EN": {
        "title": "🥗 AI Food Scanner",
        "scan": "Scan",
        "text": "Text",
        "score": "Score",
        "risk": "Risk",
        "harmful": "Harmful ingredients",
        "safe": "No harmful ingredients",
        "insights": "Insights"
    }
}[LANG]

# =========================================================
# HARMFUL E-NUMBERS (BG + EN)
# =========================================================

e_numbers = {
    "e100": ("Curcumin", "Куркумин", -5, "Natural colorant", "Естествен оцветител"),
    "e102": ("Tartrazine", "Тартразин", -20, "Hyperactivity risk", "Риск от хиперактивност"),
    "e110": ("Sunset Yellow", "Сънсет жълто", -20, "Allergy risk", "Риск от алергии"),
    "e120": ("Cochineal", "Кошенил", -15, "Allergy risk", "Алергичен риск"),

    "e211": ("Sodium Benzoate", "Натриев бензоат", -15, "Preservative risk", "Консервант риск"),
    "e220": ("Sulphur Dioxide", "Серен диоксид", -20, "Respiratory issues", "Дихателни проблеми"),
    "e250": ("Sodium Nitrite", "Натриев нитрит", -30, "Cancer risk", "Риск от рак"),

    "e320": ("BHA", "БХА", -25, "Possible carcinogen", "Възможен канцероген"),
    "e321": ("BHT", "БХТ", -25, "Hormonal disruption", "Хормонален риск"),

    "e407": ("Carrageenan", "Карагенан", -20, "Inflammation", "Възпаление"),
    "e466": ("CMC", "Карбоксиметилцелулоза", -10, "Gut irritation", "Чревно дразнене")
}

# =========================================================
# ALCOHOL (BG + EN)
# =========================================================

alcohol_keywords = {
    "alcohol": -25, "ethanol": -25, "beer": -20,
    "wine": -25, "vodka": -30, "whiskey": -30,
    "rum": -30, "fermented": -15, "malt": -10,
    "brew": -15,

    "бира": -20, "алкохол": -25, "етанол": -25,
    "вино": -25, "ракия": -30, "водка": -30,
    "уиски": -30, "ферментирал": -15,
    "малц": -10, "хмел": -10, "дрожди": -10
}

# =========================================================
# SUGAR / SWEETENERS / CARBS (NEW IMPORTANT PART)
# =========================================================

sugar_keywords = {
    "sugar": -10,
    "zahar": -10,
    "захар": -10,
    "glucose": -15,
    "глюкоза": -15,
    "fructose": -15,
    "фруктоза": -15,
    "syrup": -15,
    "сироп": -15,
    "corn syrup": -20,
    "honey": -10,
    "мед": -10,
    "dextrose": -15
}

# =========================================================
# OTHER ADDITIVES
# =========================================================

additives = {
    "flavor": -10,
    "flavour": -10,
    "aroma": -10,
    "аромат": -10,
    "color": -10,
    "colour": -10,
    "оцветител": -15,
    "preservative": -10,
    "консервант": -10
}

# =========================================================
# BEER LOGIC
# =========================================================

def detect_beer_like(text):

    signals = [
        "malt", "barley", "hops",
        "малц", "ечемик", "хмел",
        "дрожди", "ферментирал"
    ]

    hits = sum(1 for s in signals if s in text)

    if hits >= 2:
        return -25

    return 0

# =========================================================
# OCR
# =========================================================

def extract_text(image):
    img = np.array(image)
    gray = Image.fromarray(img).convert("L")

    text = pytesseract.image_to_string(gray, lang="eng")

    return text.lower()

# =========================================================
# ANALYSIS ENGINE
# =========================================================

def analyze(text):

    score = 100
    found = []
    insights = []

    # E-NUMBERS
    for k, v in e_numbers.items():
        if k in text:
            found.append(v[0])
            score += v[2]
            insights.append(v[3] + " / " + v[4])

    # ALCOHOL
    for k, v in alcohol_keywords.items():
        if k in text:
            score += v
            insights.append(f"Alcohol detected: {k}")

    # SUGAR SYSTEM
    for k, v in sugar_keywords.items():
        if k in text:
            score += v
            insights.append(f"Sugar-related: {k}")

    # ADDITIVES
    for k, v in additives.items():
        if k in text:
            score += v
            insights.append(f"Additive: {k}")

    # BEER LOGIC
    score += detect_beer_like(text)

    return found, max(0, min(100, score)), insights

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

st.title(T["title"])

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

    if st.button(T["scan"], type="primary"):

        with st.spinner("Scanning..."):

            text = extract_text(img)
            found, score, insights = analyze(text)

        # TEXT
        st.subheader(T["text"])
        st.text_area("", text, height=150)

        # SCORE
        st.subheader(T["score"])
        st.progress(score / 100)
        st.metric(T["risk"], risk_label(score))

        # INSIGHTS
        st.subheader(T["insights"])
        for i in insights:
            st.info(i)

        # HARMFUL
        st.subheader(T["harmful"])
        if found:
            for item in found:
                st.warning(item)
        else:
            st.success(T["safe"])

        # HISTORY
        st.session_state.history.append({
            "time": datetime.now(),
            "score": score
        })

        st.dataframe(pd.DataFrame(st.session_state.history))
