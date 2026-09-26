from pyrogram import Client, filters
from config import Config
from utils import chat_filter, queue_text

HELP = """<b>WatchParty Streaming Bot</b>

<b>Playback</b>
/play &lt;URL&gt; — Play a URL or reply to Telegram media
/stream &lt;URL&gt; — Stream a direct/live URL
/skip — Skip current media
/replay — Restart current media
/seek &lt;seconds&gt; — Seek forward/backward
/pause — Pause playback
/resume — Resume playback
/volume &lt;1-200&gt; — Change volume
/vcmute — Mute VC audio
/vcunmute — Unmute VC audio
/leave — Leave the video chat

<b>Info</b>
/player — Show current playback
/playlist — Show current playback and queue
/status — Show player status
/help — Show this help
"""

@Client.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(HELP, disable_web_page_preview=True)

@Client.on_message(filters.command("help"))
async def help_command(_, message):
    await message.reply_text(HELP, disable_web_page_preview=True)

@Client.on_message(filters.command("status") & chat_filter)
async def status(_, message):
    await message.reply_text(queue_text(), disable_web_page_preview=True)
