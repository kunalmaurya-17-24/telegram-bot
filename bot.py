import os
import time
import asyncio
import threading
import requests
import json
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- CONFIGURATION ---
# Render provides the PORT env var. Default to 8080 if not set.
PORT = int(os.environ.get("PORT", 8080))
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Cobalt API Inputs
COBALT_INSTANCES = [
    "https://cobalt.stream",
    "https://cobalt.kwiatekmiki.pl",
    "https://api.cobalt.xyzen.dev",
    "https://dl.cobalt.tools",
    "https://cobalt.roy.monster"
]

# Headers to avoid bot detection (Cloudflare)
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://cobalt.tools",
    "Referer": "https://cobalt.tools/"
}

# --- FLASK KEEP-ALIVE SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web_server():
    print(f"Starting Web Server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)

# --- TELEGRAM BOT LOGIC ---

def download_video_via_api(url):
    """
    Tries to download the video using the list of Cobalt API instances.
    Returns: (file_path, error_message)
    """
    filename = "downloaded_video.mp4"
    if os.path.exists(filename):
        os.remove(filename)

    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "720",
        "filenamePattern": "basic"
    }

    for instance in COBALT_INSTANCES:
        print(f"Trying API: {instance}...")
        try:
            # 1. Request Download Link
            # Try root endpoint (v10) first
            try:
                response = requests.post(f"{instance}/", headers=API_HEADERS, json=payload, timeout=15)
            except:
                # Fallback to older if root fails immediately
                continue

            if response.status_code == 404:
                 # Try legacy v7 endpoint
                 response = requests.post(f"{instance}/api/json", headers=API_HEADERS, json=payload, timeout=15)

            if response.status_code != 200:
                print(f"Instance {instance} failed with {response.status_code}")
                continue

            try:
                data = response.json()
            except:
                continue # not json

            # Find the URL
            download_url = data.get("url")
            if not download_url and "picker" in data:
                 for item in data["picker"]:
                     if "url" in item:
                         download_url = item["url"]
                         break
            
            if not download_url:
                continue

            # 2. Download the File
            print(f"Downloading from: {download_url}")
            video_resp = requests.get(download_url, headers=API_HEADERS, stream=True, timeout=60)
            
            if video_resp.status_code == 200:
                with open(filename, "wb") as f:
                    for chunk in video_resp.iter_content(chunk_size=4096):
                        if chunk: f.write(chunk)
                
                # Verify file size > 0
                if os.path.getsize(filename) > 0:
                    return filename, None
            
        except Exception as e:
            print(f"Error with {instance}: {e}")
            continue
            
    return None, "All API instances failed."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Please send a valid YouTube link.")
        return

    status_msg = await update.message.reply_text("🔎 Searching for video...")

    # Run API download in a thread to not block the bot loop
    file_path, error = await asyncio.to_thread(download_video_via_api, url)

    if not file_path:
        await status_msg.edit_text(f"❌ Failed to download. {error}")
        return

    # Check File Size (Telegram Limit is 50MB for bots usually)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 49:
        await status_msg.edit_text("❌ Video is too large (>50MB) for Telegram.")
        os.remove(file_path)
        return

    await status_msg.edit_text("📤 Uploading...")
    
    try:
        with open(file_path, "rb") as video:
            await update.message.reply_video(video=video)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error uploading: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing!")
        return

    # 1. Start Flask Server in a Background Thread
    # This prevents Render from putting the app to sleep (reqs: binds to PORT)
    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()

    # 2. Start Telegram Bot
    print("Bot starting polling...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
