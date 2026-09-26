from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from utils import admin_filter, chat_filter, add_to_queue, media_from_message, stream_from_link, leave_call, get_link, queue_text

@Client.on_message(filters.command(["play", f"play@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def play_command(_, message: Message):
    item, error = await media_from_message(message)
    if error:
        await message.reply_text(error)
        return
    await add_to_queue(item)
    await message.reply_text(queue_text(), disable_web_page_preview=True)

@Client.on_message(filters.command(["stream", f"stream@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def stream_command(_, message: Message):
    if len(message.command) >= 2:
        link = " ".join(message.command[1:]).strip()
    elif message.reply_to_message and message.reply_to_message.text:
        link = message.reply_to_message.text.strip()
    else:
        await message.reply_text("Usage: /stream <URL>")
        return
    if not link.startswith(("http://", "https://")):
        await message.reply_text("Please provide a valid HTTP/HTTPS URL.")
        return
    resolved = await get_link(link)
    if not resolved:
        await message.reply_text("Unable to resolve the stream URL.")
        return
    ok, error = await stream_from_link(link, title="Live Stream")
    await message.reply_text("✅ Stream started." if ok else f"❌ {error or 'Unable to start stream.'}")

@Client.on_message(filters.command(["leave", f"leave@{Config.BOT_USERNAME}"]) & chat_filter & admin_filter)
async def leave_command(_, message: Message):
    await leave_call()
    await message.reply_text("✅ Left the video chat.")
