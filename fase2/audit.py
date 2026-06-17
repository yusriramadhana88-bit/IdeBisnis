import anthropic
import json
import re

client = anthropic.Anthropic()

CATEGORIZE_PROMPT = """Kamu adalah asisten keuangan personal.
Dari daftar pengeluaran berikut, kelompokkan per kategori (misalnya: Makanan, Transport, Belanja, Hiburan, Utilitas, dll).

Data pengeluaran (format: merchant | items | total):
{expenses}

Jawab dalam format JSON:
{{
  "categories": [
    {{
      "name": "Nama Kategori",
      "total": angka_IDR,
      "count": jumlah_transaksi,
      "merchants": ["merchant1", "merchant2"]
    }}
  ]
}}

Aturan:
- Gabungkan merchant yang sejenis ke satu kategori
- Urutkan dari total terbesar ke terkecil
- Jawab HANYA dengan JSON, tanpa teks lain
"""


def categorize_expenses(rows) -> list[dict]:
    if not rows:
        return []

    lines = []
    for r in rows:
        lines.append(f"{r['merchant']} | {r['items']} | {r['total']}")

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": CATEGORIZE_PROMPT.format(expenses="\n".join(lines))
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw)
    return data.get("categories", [])


def format_audit_reply(categories: list[dict], grand_total: float) -> str:
    lines = ["*📊 Audit Pengeluaran Bulan Ini*", ""]

    for i, cat in enumerate(categories, 1):
        pct = (cat["total"] / grand_total * 100) if grand_total else 0
        lines.append(f"*{i}. {cat['name']}* — Rp {cat['total']:,.0f} ({pct:.0f}%)")
        for m in cat.get("merchants", []):
            lines.append(f"   └ {m}")
        lines.append("")

    lines.append(f"*Total: Rp {grand_total:,.0f}*")
    lines.append("")
    lines.append(
        "💡 *Mau hemat di kategori mana?*\n"
        "Balas dengan format:\n"
        "`hemat [nomor] [target_rupiah]`\n\n"
        "Contoh: `hemat 1 500000` → hemat Rp 500.000 di kategori pertama\n"
        "Bisa kirim beberapa baris sekaligus."
    )
    return "\n".join(lines)


def format_savings_summary(targets: list[dict]) -> str:
    total_savings = sum(t["target_amount"] for t in targets)
    lines = ["*✅ Target Penghematan Disimpan!*", ""]
    for t in targets:
        lines.append(f"• {t['category']} — hemat Rp {t['target_amount']:,.0f}/bulan")
    lines.append("")
    lines.append(f"*Total potensi hemat: Rp {total_savings:,.0f}/bulan*")
    lines.append("")
    lines.append(
        f"🕌 Kalau kamu konsisten, kamu bisa kumpulkan "
        f"*Rp {total_savings:,.0f} tambahan per bulan* untuk tabungan haji!"
    )
    lines.append(f"Setahun = *Rp {total_savings * 12:,.0f}*")
    return "\n".join(lines)
