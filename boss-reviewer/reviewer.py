import anthropic
import json
import re

client = anthropic.Anthropic()

TYPO_PROMPT = """Kamu adalah proofreader profesional Bahasa Indonesia.
Periksa teks berikut untuk menemukan TYPO (kesalahan ketik/ejaan).

HANYA laporkan typo yang jelas — kata yang salah eja, huruf tertukar, huruf hilang.
JANGAN laporkan masalah gaya bahasa, tanda baca, atau pilihan kata yang valid.

Teks (setiap baris diawali nomor paragraf):
{text}

Jawab dalam format JSON array:
[
  {{
    "paragraph": nomor_paragraf,
    "word": "kata_yang_salah",
    "suggestion": "kata_yang_benar",
    "context": "...potongan kalimat sekitar kata salah..."
  }}
]

Jika tidak ada typo, jawab: []
Jawab HANYA dengan JSON, tanpa teks lain.
"""


def check_typos(paragraphs: list[dict]) -> list[dict]:
    if not paragraphs:
        return []

    lines = []
    for p in paragraphs:
        lines.append(f"[{p['index']}] {p['text']}")

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": TYPO_PROMPT.format(text="\n".join(lines))
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)
