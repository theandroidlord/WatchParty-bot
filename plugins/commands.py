from pyrogram import Client, filters
from config import Config
from utils import chat_filter, queue_text

HELP = """<b>WatchParty streaming bot</b>

<b>Playback</b>
/play &lt;URL&gt; or reply to Telegram media
/stream &lt;live/direct URL&gt;
/player - current stream and queue
/skip
/replay
/seek &lt;seconds&gt;
/pause /resume
/volume &lt;1-200&gt;
/vcmute /vcunmute
/leave
"""

@Client.on_message(filters.command(["start", f"start@{Config.BOT_USERNAME}"]))
async def start(_, message):
    await message.reply_text(HELP, disable_web_page_preview=True)

@Client.on_message(filters.command(["help", f"help@{Config.BOT_USERNAME}"]))
async def help_command(_, message):
    await message.reply_text(HELP, disable_web_page_preview=True)

@Client.on_message(filters.command(["status", f"status@{Config.BOT_USERNAME}"]) & chat_filter)
async def status(_, message):
    await message.reply_text(queue_text(), disable_web_page_preview=True)
