from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from utils import admin_filter, chat_filter, skip, pause, resume, volume, mute, unmute, restart_playout, seek_file, queue_text

@Client.on_message(filters.command(["skip", f"skip@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def skip_command(_, message: Message):
    await skip()
    await message.reply_text(queue_text(), disable_web_page_preview=True)

@Client.on_message(filters.command(["pause", f"pause@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def pause_command(_, message: Message):
    await message.reply_text("✅ Paused." if await pause() else "❌ Unable to pause.")

@Client.on_message(filters.command(["resume", f"resume@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def resume_command(_, message: Message):
    await message.reply_text("✅ Resumed." if await resume() else "❌ Unable to resume.")

@Client.on_message(filters.command(["volume", f"volume@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def volume_command(_, message: Message):
    try:
        value = int(message.command[1])
    except (IndexError, ValueError):
        await message.reply_text("Usage: /volume <1-200>")
        return
    if not 1 <= value <= 200:
        await message.reply_text("Volume must be between 1 and 200.")
        return
    await message.reply_text(f"✅ Volume: {value}" if await volume(value) else "❌ Unable to change volume.")

@Client.on_message(filters.command(["vcmute", f"vcmute@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def mute_command(_, message: Message):
    await message.reply_text("🔇 Muted." if await mute() else "❌ Unable to mute.")

@Client.on_message(filters.command(["vcunmute", f"vcunmute@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def unmute_command(_, message: Message):
    await message.reply_text("🔊 Unmuted." if await unmute() else "❌ Unable to unmute.")

@Client.on_message(filters.command(["replay", f"replay@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def replay_command(_, message: Message):
    await message.reply_text("✅ Replaying." if await restart_playout() else "❌ Nothing is playing.")

@Client.on_message(filters.command(["player", f"player@{Config.BOT_USERNAME}", "playlist", f"playlist@{Config.BOT_USERNAME}"]) & chat_filter)
async def player_command(_, message: Message):
    await message.reply_text(queue_text(), disable_web_page_preview=True)

@Client.on_message(filters.command(["seek", f"seek@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def seek_command(_, message: Message):
    try:
        offset = int(message.command[1])
    except (IndexError, ValueError):
        await message.reply_text("Usage: /seek <seconds>  (negative values rewind)")
        return
    ok, error = await seek_file(offset)
    await message.reply_text("✅ Seeked." if ok else f"❌ {error or 'Unable to seek.'}")
