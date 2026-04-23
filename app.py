from flask import Flask, request, jsonify
import cv2
from pyzbar.pyzbar import decode
import requests
import easyocr
import numpy as np

app = Flask(__name__)

# OCR reader
reader = easyocr.Reader(['en', 'bg'])

def scan_barcode(image):
    barcodes = decode(image)
    for barcode in barcodes:
        return barcode.data.decode("utf-8")
    return None

def get_product_info(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()

    if data["status"] != 1:
        return None

    product = data["product"]

    return {
        "name": product.get("product_name"),
        "brands": product.get("brands"),
        "ingredients": product.get("ingredients_text"),
        "nutriments": product.get("nutriments"),
        "allergens": product.get("allergens"),
        "nutrition_grade": product.get("nutrition_grade_fr")
    }

def analyze_health(info):
    warnings = []

    if not info:
        return ["Няма информация"]

    ingredients = (info.get("ingredients") or "").lower()

    if "sugar" in ingredients:
        warnings.append("Високо съдържание на захар – риск от диабет")

    if "palm oil" in ingredients:
        warnings.append("Съдържа палмово масло – възможен риск за сърцето")

    if "salt" in ingredients:
        warnings.append("Високо съдържание на сол – риск от високо кръвно")

    return warnings

@app.route("/scan", methods=["POST"])
def scan():
    file = request.files["image"]
    image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)

    barcode = scan_barcode(image)

    if not barcode:
        # fallback към OCR
        result = reader.readtext(image)
        text = " ".join([res[1] for res in result])
        return jsonify({
            "error": "Не е намерен баркод",
            "ocr_text": text
        })

    product_info = get_product_info(barcode)
    health_analysis = analyze_health(product_info)

    return jsonify({
        "barcode": barcode,
        "product_info": product_info,
        "health_analysis": health_analysis
    })

if __name__ == "__main__":
    app.run(debug=True)
