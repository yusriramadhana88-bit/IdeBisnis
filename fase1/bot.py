import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.database import init_db, get_conn
from fase1.ocr import parse_receipt, format_receipt_reply

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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    log.info("NabungHaji Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
