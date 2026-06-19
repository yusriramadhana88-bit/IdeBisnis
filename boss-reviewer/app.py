import os
import json
import re
import uuid
from pathlib import Path

from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from docx_parser import extract_paragraphs_from_docx
from reviewer import check_typos, check_diksi, check_koherensi

load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = Path(__file__).parent / "uploads"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

ALLOWED_FREE = {".docx"}
ALLOWED_PREMIUM = {".docx", ".pdf"}
FREE_LIMIT = 5


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("document")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded"}), 400

    ext = Path(file.filename).suffix.lower()
    is_premium = request.form.get("premium") == "1"

    features = {
        "typo": request.form.get("feat_typo") == "1",
        "diksi": request.form.get("feat_diksi") == "1",
        "koherensi": request.form.get("feat_koherensi") == "1",
    }
    if not any(features.values()):
        features["typo"] = True

    allowed = ALLOWED_PREMIUM if is_premium else ALLOWED_FREE
    if ext not in allowed:
        msg = "Format .pdf hanya untuk Premium." if ext == ".pdf" else f"Format {ext} tidak didukung."
        return jsonify({"error": msg}), 400

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = app.config["UPLOAD_FOLDER"] / filename
    file.save(filepath)

    try:
        paragraphs = extract_paragraphs_from_docx(filepath)
        all_findings = []

        if features["typo"]:
            all_findings.extend(check_typos(paragraphs))
        if features["diksi"]:
            all_findings.extend(check_diksi(paragraphs))
        if features["koherensi"]:
            all_findings.extend(check_koherensi(paragraphs))

        total_found = len(all_findings)
        is_limited = not is_premium and total_found > FREE_LIMIT
        visible = all_findings[:FREE_LIMIT] if not is_premium else all_findings

        return jsonify({
            "paragraphs": paragraphs,
            "findings": visible,
            "total_found": total_found,
            "is_limited": is_limited,
            "is_premium": is_premium,
            "features": features,
        })
    finally:
        filepath.unlink(missing_ok=True)


if __name__ == "__main__":
    app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)
    app.run(debug=True, port=5000)
