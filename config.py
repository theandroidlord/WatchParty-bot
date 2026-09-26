#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    SESSION = os.environ.get("SESSION_STRING", "")
    CHAT = int(os.environ.get("CHAT", "0"))
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split() if x.isdigit()]
    BITRATE = int(os.environ.get("BITRATE", "48000"))
    FPS = int(os.environ.get("FPS", "30"))
    QUALITY = int(float(os.environ.get("QUALITY", "100")))

    GET_FILE = {}
    DATA = {}
    DUR = {}
    playlist = []
    current = None
    current_file = None
    CALL_STATUS = False
    PAUSE = False
    MUTED = False
    VOLUME = 100
    BOT_USERNAME = None
    USER_ID = None
    STARTUP_ERROR = None
