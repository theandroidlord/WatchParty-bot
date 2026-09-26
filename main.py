import asyncio
import os

import yt_dlp
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import AudioQuality, ChatUpdate, MediaStream, StreamEnded, VideoQuality

import config


bot = Client(
    "watchparty_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
)

assistant = Client(
    "watchparty_assistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    in_memory=True,
)

# PyTgCalls stores the current event loop when it is constructed.
# Keep this same loop for the complete application lifetime.
app_loop = asyncio.get_event_loop()
calls = PyTgCalls(assistant)

current_file = None
download_lock = asyncio.Lock()


def allowed(message):
    if message.chat.id != config.CHAT_ID:
        return False
    return not config.ADMINS or (
        message.from_user and message.from_user.id in config.ADMINS
    )


def bar(percent, width=14):
    percent = max(0, min(100, int(percent)))
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def human_bytes(value):
    value = float(value or 0)
    units = ("B", "KB", "MB", "GB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024


def progress_text(state):
    percent = state.get("percent", 0)
    downloaded = state.get("downloaded", 0)
    total = state.get("total", 0)
    speed = state.get("speed", 0)

    if total:
        size = f"{human_bytes(downloaded)} / {human_bytes(total)}"
    else:
        size = human_bytes(downloaded)

    return (
        "⬇️ <b>Downloading video</b>\n\n"
        f"<code>{bar(percent)}</code> {percent:3d}%\n"
        f"📦 {size}\n"
        f"⚡ {human_bytes(speed)}/s"
    )


async def update_progress(message, state):
    last = ""
    while not state.get("done"):
        text = progress_text(state)
        if text != last:
            try:
                await message.edit_text(text)
                last = text
            except Exception:
                pass
        await asyncio.sleep(2)


def ytdlp_hook(state):
    def hook(data):
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            state["total"] = total
            state["downloaded"] = downloaded
            state["speed"] = data.get("speed") or 0
            state["percent"] = int(downloaded * 100 / total) if total else 0
    return hook


async def download_video(url, progress_message):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

    state = {
        "percent": 0,
        "downloaded": 0,
        "total": 0,
        "speed": 0,
        "done": False,
    }

    task = asyncio.create_task(update_progress(progress_message, state))

    def download():
        options = {
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(config.DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [ytdlp_hook(state)],
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if info.get("requested_downloads"):
                merged = os.path.splitext(filename)[0] + ".mp4"
                if os.path.exists(merged):
                    filename = merged

            return filename, info.get("title") or "Video"

    try:
        filename, title = await asyncio.to_thread(download)

        # Only stop the progress task after yt-dlp and any FFmpeg merge/post-processing
        # have completely returned.
        state["done"] = True
        state["percent"] = 100
        await task

        if not os.path.isfile(filename):
            raise FileNotFoundError(
                "yt-dlp finished but the output file was not found."
            )

        await progress_message.edit_text(
            f"✅ <b>Downloaded</b>\n<code>{title}</code>\n\n"
            f"<code>{bar(100)}</code> 100%"
        )
        return filename, title

    except Exception:
        state["done"] = True
        await task
        raise


async def play_file(path):
    global current_file

    old_file = current_file

    stream = MediaStream(
        path,
        AudioQuality.HIGH,
        VideoQuality.HD_720p,
    )

    await calls.play(config.CHAT_ID, stream)
    current_file = path

    # The new stream is active, so the previous local file is no longer needed.
    if old_file and old_file != path and os.path.isfile(old_file):
        try:
            os.remove(old_file)
        except OSError:
            pass


async def cleanup_file():
    global current_file

    path = current_file
    current_file = None

    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


@bot.on_message(filters.command("join"))
async def join_command(_, message):
    if not allowed(message):
        return

    try:
        await calls.play(config.CHAT_ID)
        await message.reply_text("✅ Joined the current video chat.")
    except Exception as e:
        await message.reply_text(
            "❌ Could not join the video chat. "
            "Start a Telegram voice/video chat first.\n\n"
            f"<code>{e}</code>"
        )


@bot.on_message(filters.command("play"))
async def play_command(_, message):
    if not allowed(message):
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: /play <YouTube or direct video URL>")
        return

    url = " ".join(message.command[1:]).strip()

    if not url.startswith(("http://", "https://")):
        await message.reply_text("❌ Please send a valid HTTP/HTTPS URL.")
        return

    async with download_lock:
        status = await message.reply_text(
            "⬇️ <b>Preparing video...</b>\n"
            "<code>░░░░░░░░░░░░░░</code> 0%"
        )

        try:
            filename, title = await download_video(url, status)
            await play_file(filename)

            await status.edit_text(
                "▶️ <b>Now playing</b>\n"
                f"<code>{title}</code>\n\n"
                "🎥 720p video\n"
                "<code>██████████████</code> 100%"
            )

        except Exception as e:
            await cleanup_file()
            await status.edit_text(
                "❌ <b>Playback failed</b>\n\n"
                f"<code>{e}</code>"
            )


@bot.on_message(filters.command("pause"))
async def pause_command(_, message):
    if not allowed(message):
        return

    try:
        await calls.pause(config.CHAT_ID)
        await message.reply_text("⏸️ Paused.")
    except Exception as e:
        await message.reply_text(f"❌ Pause failed.\n<code>{e}</code>")


@bot.on_message(filters.command("leave"))
async def leave_command(_, message):
    if not allowed(message):
        return

    try:
        await calls.leave_call(config.CHAT_ID)
    except Exception:
        pass

    await cleanup_file()
    await message.reply_text("👋 Left the video chat.")


@calls.on_update(
    call_filters.chat_update(
        ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP
    )
)
async def call_left(_, update):
    await cleanup_file()


@calls.on_update(call_filters.stream_end())
async def stream_ended(_, update: StreamEnded):
    await cleanup_file()


async def start_client(client):
    while True:
        try:
            await client.start()
            return
        except FloodWait as e:
            await asyncio.sleep(int(e.value) + 5)


async def main():
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

    await start_client(bot)
    await start_client(assistant)

    calls.start()

    me = await assistant.get_me()
    print(f"Assistant: @{me.username or me.id}", flush=True)
    print("WatchParty started.", flush=True)
    print("Commands: /join /play /pause /leave", flush=True)

    # Keep the same event loop alive. Pyrogram's legacy sync idle helper is
    # intentionally avoided because this application already owns the loop.
    await asyncio.Event().wait()


if __name__ == "__main__":
    app_loop.run_until_complete(main())
