#!/usr/bin/env python3
from pyrogram import Client
from pytgcalls import PyTgCalls

from config import Config

USER = Client(
    "UserSession",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    session_string=Config.SESSION,
    in_memory=True,
)

group_call = PyTgCalls(USER)
