import os
import time
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    DOWNLOAD_DIR,
    MAX_FILE_SIZE_MB,
    WAIT_TIMEOUT_SECONDS,
)
from downloader import download_video

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Send a valid YouTube link.")
        return

    await update.message.reply_text("Downloading...")

    try:
        # Run yt-dlp in background thread
        file_path = await asyncio.to_thread(
            download_video, url, DOWNLOAD_DIR
        )

        # Wait until THIS EXACT file exists (no directory scanning)
        start_time = time.time()
        while not os.path.exists(file_path):
            if time.time() - start_time > WAIT_TIMEOUT_SECONDS:
                await update.message.reply_text(
                    "Failed to process the video."
                )
                return
            await asyncio.sleep(2)

        # File size check
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            os.remove(file_path)
            await update.message.reply_text(
                "Video too large to send on Telegram."
            )
            return

        # Send video
        with open(file_path, "rb") as video:
            await update.message.reply_video(video=video)

        # Cleanup
        os.remove(file_path)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("Failed to process the video.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
