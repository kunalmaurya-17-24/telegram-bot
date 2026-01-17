import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE_MB = 2000
WAIT_TIMEOUT_SECONDS = 120
