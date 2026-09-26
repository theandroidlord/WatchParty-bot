from pyrogram import Client, filters
from config import Config
from utils import chat_filter, queue_text

HELP = """<b>WatchParty Streaming Bot</b>

<b>Playback Commands</b>
/play &lt;URL&gt; — Play a YouTube or supported media URL, or reply to a Telegram video/audio.
/stream &lt;URL&gt; — Start a direct/live HTTP or HTTPS stream in the VC.
/skip — Stop the current media and play the next item in the queue.
/replay — Restart the currently playing media from the beginning.
/seek &lt;seconds&gt; — Move forward or backward by the specified number of seconds.
/pause — Pause the current stream.
/resume — Resume paused playback.
/volume &lt;1-200&gt; — Set playback volume from 1 to 200.
/vcmute — Mute the bot's VC audio.
/vcunmute — Unmute the bot's VC audio.
/leave — Leave the current Telegram video chat.

<b>Information Commands</b>
/player — Show the currently playing media and playback position.
/playlist — Show the current media and all queued items.
/status — Show the current player status.
/help — Show this command list and usage information.
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
