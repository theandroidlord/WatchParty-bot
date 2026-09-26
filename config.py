import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]
CHAT_ID = int(os.environ["CHAT_ID"])

ADMINS = {
    int(x) for x in os.getenv("ADMINS", "").replace(",", " ").split()
    if x.strip().lstrip("-").isdigit()
}

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
