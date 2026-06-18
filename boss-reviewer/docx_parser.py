from pathlib import Path
from docx import Document


def extract_paragraphs_from_docx(filepath: Path) -> list[dict]:
    doc = Document(str(filepath))
    paragraphs = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            paragraphs.append({"index": i, "text": text})
    return paragraphs
