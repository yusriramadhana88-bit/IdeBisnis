import anthropic
import json
import re

client = anthropic.Anthropic()


def _call_claude(prompt: str, text_lines: list[str], model: str = "claude-haiku-4-5-20251001") -> list[dict]:
    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt.format(text="\n".join(text_lines))}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def _build_lines(paragraphs: list[dict]) -> list[str]:
    return [f"[{p['index']}] {p['text']}" for p in paragraphs]


# ─── Typo Checker ───

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
    results = _call_claude(TYPO_PROMPT, _build_lines(paragraphs))
    for r in results:
        r["type"] = "typo"
    return results


# ─── Konsistensi Diksi ───

DIKSI_PROMPT = """Kamu adalah editor profesional Bahasa Indonesia.
Periksa teks berikut untuk menemukan INKONSISTENSI DIKSI — yaitu kata/istilah yang sama
ditulis dengan cara berbeda di paragraf berbeda.

Contoh inkonsistensi:
- "analisa" di paragraf 2 tapi "analisis" di paragraf 5
- "di mana" di paragraf 1 tapi "dimana" di paragraf 3
- "e-mail" di paragraf 2 tapi "email" di paragraf 6
- Singkatan: "Rp." vs "Rp" vs "IDR"

Teks (setiap baris diawali nomor paragraf):
{text}

Jawab dalam format JSON array:
[
  {{
    "paragraph": nomor_paragraf_yang_sebaiknya_diubah,
    "word": "kata_yang_inkonsisten",
    "suggestion": "kata_yang_konsisten_sesuai_KBBI/EYD",
    "context": "...potongan kalimat...",
    "note": "Juga ditulis sebagai 'X' di paragraf N"
  }}
]

Jika tidak ada inkonsistensi, jawab: []
Jawab HANYA dengan JSON, tanpa teks lain.
"""


def check_diksi(paragraphs: list[dict]) -> list[dict]:
    if not paragraphs:
        return []
    results = _call_claude(DIKSI_PROMPT, _build_lines(paragraphs))
    for r in results:
        r["type"] = "diksi"
    return results


# ─── Koherensi Paragraf ───

KOHERENSI_PROMPT = """Kamu adalah editor profesional Bahasa Indonesia.
Periksa teks berikut untuk menemukan masalah KOHERENSI PARAGRAF — yaitu kalimat penjelas
yang tidak mendukung atau menyimpang dari ide utama paragrafnya.

Fokus HANYA pada:
- Kalimat yang tidak relevan dengan topik paragrafnya
- Transisi antar kalimat yang membingungkan
- Kalimat yang seharusnya ada di paragraf lain

JANGAN komentari kualitas penulisan secara umum.

Teks (setiap baris diawali nomor paragraf):
{text}

Jawab dalam format JSON array:
[
  {{
    "paragraph": nomor_paragraf,
    "word": "kalimat_bermasalah_disingkat_5_kata",
    "suggestion": "Penjelasan singkat masalah dan saran perbaikan",
    "context": "...kalimat lengkap yang bermasalah..."
  }}
]

Jika tidak ada masalah koherensi, jawab: []
Jawab HANYA dengan JSON, tanpa teks lain.
"""


def check_koherensi(paragraphs: list[dict]) -> list[dict]:
    if not paragraphs:
        return []
    results = _call_claude(KOHERENSI_PROMPT, _build_lines(paragraphs), model="claude-sonnet-4-6-20250514")
    for r in results:
        r["type"] = "koherensi"
    return results
