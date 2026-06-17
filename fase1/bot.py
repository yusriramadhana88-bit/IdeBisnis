import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
import re
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.database import init_db, get_conn
from fase1.ocr import parse_receipt, format_receipt_reply
from fase2.audit import categorize_expenses, format_audit_reply, format_savings_summary

load_dotenv(Path(__file__).parent.parent / ".env")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Saya *NabungHaji Bot* 🕌\n\n"
        "Kirim foto struk belanja kamu, saya akan otomatis mencatat pengeluarannya.\n\n"
        "Perintah yang tersedia:\n"
        "/rekap — lihat total pengeluaran bulan ini\n"
        "/audit — breakdown per kategori + atur target hemat\n"
        "/start — pesan ini",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_rekap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = get_conn()
    rows = conn.execute(
        """SELECT merchant, date, total FROM expenses
           WHERE user_id = ? AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')
           ORDER BY created_at DESC""",
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Belum ada struk yang dicatat bulan ini.")
        return

    total = sum(r["total"] for r in rows)
    lines = ["*Rekap bulan ini:*", ""]
    for r in rows:
        date = r["date"] or "?"
        lines.append(f"• {r['merchant']} ({date}) — Rp {r['total']:,.0f}")
    lines += ["", f"*Total: Rp {total:,.0f}*"]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_audit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = get_conn()
    rows = conn.execute(
        """SELECT merchant, items, total FROM expenses
           WHERE user_id = ? AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')
           ORDER BY total DESC""",
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Belum ada struk bulan ini. Kirim foto struk dulu ya!")
        return

    msg = await update.message.reply_text("🔍 Menganalisis pengeluaran...")

    try:
        categories = categorize_expenses(rows)
        grand_total = sum(r["total"] for r in rows)
        ctx.user_data["audit_categories"] = categories
        reply = format_audit_reply(categories, grand_total)
        await msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        log.error(f"Audit error: {e}")
        await msg.edit_text("❌ Gagal menganalisis pengeluaran. Coba lagi nanti.")


async def handle_hemat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    categories = ctx.user_data.get("audit_categories")
    if not categories:
        await update.message.reply_text("Jalankan /audit dulu sebelum mengatur target hemat.")
        return

    text = update.message.text.strip()
    lines = text.split("\n")
    targets = []
    month = __import__("datetime").date.today().strftime("%Y-%m")

    for line in lines:
        match = re.match(r"hemat\s+(\d+)\s+([\d.]+)", line.strip(), re.IGNORECASE)
        if not match:
            continue
        idx = int(match.group(1)) - 1
        amount = float(match.group(2).replace(".", ""))
        if 0 <= idx < len(categories):
            targets.append({"category": categories[idx]["name"], "target_amount": amount})

    if not targets:
        await update.message.reply_text(
            "Format tidak dikenali. Gunakan:\n`hemat [nomor] [target_rupiah]`\nContoh: `hemat 1 500000`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    conn = get_conn()
    for t in targets:
        conn.execute(
            """INSERT INTO savings_targets (user_id, category, target_amount, month)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, category, month)
               DO UPDATE SET target_amount = excluded.target_amount""",
            (user_id, t["category"], t["target_amount"], month)
        )
    conn.commit()
    conn.close()

    reply = format_savings_summary(targets)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    msg = await update.message.reply_text("📷 Memproses struk...")

    try:
        photo = update.message.photo[-1]  # highest resolution
        file = await ctx.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        data = parse_receipt(bytes(image_bytes))

        conn = get_conn()
        conn.execute(
            "INSERT INTO expenses (user_id, date, merchant, items, total) VALUES (?,?,?,?,?)",
            (user_id, data.get("date"), data.get("merchant"), str(data.get("items", [])), data.get("total", 0))
        )
        conn.commit()
        conn.close()

        reply = format_receipt_reply(data)
        await msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        log.error(f"OCR error: {e}")
        await msg.edit_text("❌ Gagal membaca struk. Pastikan foto jelas dan coba lagi.")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rekap", cmd_rekap))
    app.add_handler(CommandHandler("audit", cmd_audit))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^hemat\s") & filters.TEXT, handle_hemat))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    log.info("NabungHaji Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
