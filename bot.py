import os
import re
import asyncio
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

DOWNLOAD_DIR = "tmp"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/shorts/|youtu\.be/)[\w\-]+"
)

# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send a YouTube Shorts link and I’ll download it."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not YOUTUBE_REGEX.search(text):
        await update.message.reply_text("Send a valid YouTube Shorts link.")
        return

    await update.message.reply_text("Downloading...")

    video_path = None

    try:
        video_path = await download_short(text)

        if not video_path or not os.path.exists(video_path):
            raise RuntimeError("Download failed")

        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(video_path, "rb"),
            supports_streaming=True,
        )

    except Exception:
        await update.message.reply_text("Failed to process the video.")

    finally:
        # CLEANUP (CRITICAL)
        if video_path and os.path.exists(video_path):
            os.remove(video_path)


# ================= DOWNLOAD LOGIC =================

async def download_short(url: str) -> str:
    filename = f"{os.getpid()}_{asyncio.get_running_loop().time()}.mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    cmd = [
        "yt-dlp",
        "-f", "mp4",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "--socket-timeout", "20",
        "--retries", "3",
        "-o", output_path,
        url,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        await asyncio.wait_for(process.communicate(), timeout=90)
    except asyncio.TimeoutError:
        process.kill()
        return None

    return output_path if os.path.exists(output_path) else None


# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Bot started.")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
