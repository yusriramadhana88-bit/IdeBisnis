import anthropic
import base64
import json
import re

client = anthropic.Anthropic()

PARSE_PROMPT = """Kamu adalah asisten OCR struk belanja.
Dari gambar struk ini, ekstrak informasi berikut dalam format JSON:
{
  "merchant": "nama toko/restoran",
  "date": "tanggal (YYYY-MM-DD jika tersedia, null jika tidak)",
  "items": [
    {"name": "nama item", "qty": angka, "price": angka_IDR}
  ],
  "total": angka_IDR,
  "currency": "IDR"
}

Aturan:
- Harga selalu dalam Rupiah (buang titik/koma pemisah ribuan, jadikan integer)
- Kalau ada item yang tidak jelas, masukkan saja dengan nama aslinya
- Kalau total tidak terbaca, hitung dari sum items
- Jawab HANYA dengan JSON, tanpa teks lain
"""

def parse_receipt(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": PARSE_PROMPT}
            ]
        }]
    )
    raw = msg.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)

def format_receipt_reply(data: dict) -> str:
    merchant = data.get("merchant", "Tidak diketahui")
    date = data.get("date") or "Tanggal tidak terbaca"
    total = data.get("total", 0)
    items = data.get("items", [])

    lines = [f"*{merchant}*", f"📅 {date}", ""]
    for item in items:
        name = item.get("name", "-")
        qty = item.get("qty", 1)
        price = item.get("price", 0)
        lines.append(f"• {name} (x{qty}) — Rp {price:,.0f}")

    lines += ["", f"*Total: Rp {total:,.0f}*"]
    lines += ["", "✅ Struk berhasil dicatat!"]
    return "\n".join(lines)
