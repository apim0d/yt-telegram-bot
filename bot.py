import os
import asyncio
import tempfile
import subprocess
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "ytbot"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

user_links = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ابعت رابط اليوتيوب وهتختار الجودة بنفسك.")

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_links[update.message.chat_id] = url

    keyboard = [
        [InlineKeyboardButton("🎵 صوت فقط", callback_data="audio")],
        [InlineKeyboardButton("📱 720p", callback_data="720")],
        [InlineKeyboardButton("💻 1080p", callback_data="1080")]
    ]

    await update.message.reply_text(
        "اختر الجودة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def download_video(url, quality):
    output = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

    if quality == "audio":
        cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output, url]
    elif quality == "720":
        cmd = ["yt-dlp", "-f", "bv*[height<=720]+ba/best", "-o", output, url]
    else:
        cmd = ["yt-dlp", "-f", "bv*[height<=1080]+ba/best", "-o", output, url]

    subprocess.run(cmd, check=True)

async def quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    url = user_links.get(chat_id)

    quality = query.data
    await query.edit_message_text("⏳ جاري التحميل...")

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, download_video, url, quality)

        files = list(DOWNLOAD_DIR.glob("*"))
        file = max(files, key=lambda x: x.stat().st_mtime)

        with open(file, "rb") as f:
            await context.bot.send_document(chat_id=chat_id, document=f)

        file.unlink()
        await context.bot.send_message(chat_id, "✅ تم الإرسال بنجاح")

    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ خطأ: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_link))
    app.add_handler(CallbackQueryHandler(quality_choice))
    app.run_polling()
