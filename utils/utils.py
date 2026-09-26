import asyncio, json, os, re, time

import yt_dlp
from pyrogram import enums, filters
from pyrogram.errors import PeerIdInvalid, ChannelInvalid
from pyrogram.types import Message
from pytgcalls.types import AudioQuality, MediaStream, VideoQuality

from bot import bot
from config import Config
from .logger import LOGGER
from .pyro_dl import Downloader

dl = Downloader()


async def get_admins(chat_id):
    ids = set(Config.ADMINS)
    try:
        async for member in bot.get_chat_members(
            chat_id,
            filter=enums.ChatMembersFilter.ADMINISTRATORS,
        ):
            ids.add(member.user.id)
    except Exception as e:
        LOGGER.warning("Could not load chat admins: %s", e)
    return list(ids)


async def is_admin(_, client, message: Message):
    if message.from_user is None:
        return bool(message.sender_chat)
    return message.from_user.id in await get_admins(Config.CHAT)


def valid_chat(_, client, message: Message):
    return (
        message.chat.type == enums.ChatType.PRIVATE
        or message.chat.id == Config.CHAT
    )


chat_filter = filters.create(valid_chat)
admin_filter = filters.create(is_admin)


def is_ytdl_supported(url):
    try:
        return any(
            x.suitable(url) and x.IE_NAME != "generic"
            for x in yt_dlp.extractor.gen_extractors()
        )
    except Exception:
        return False


async def get_link(url):
    if not is_ytdl_supported(url):
        return url

    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "--geo-bypass",
        "-g",
        "-f",
        "best[height<=?720][width<=?1280]/best",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()

    if proc.returncode != 0 or not out:
        LOGGER.error("yt-dlp failed: %s", err.decode(errors="ignore"))
        return None

    return out.decode().strip().splitlines()[-1]


async def get_duration(path):
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()

    try:
        value = json.loads(out.decode()).get("format", {}).get("duration")
        return float(value) if value else 0
    except Exception:
        return 0


async def _resolve(item):
    if item["kind"] == "telegram":
        path = Config.GET_FILE.get(item["id"])

        if not path:
            path = await dl.pyro_dl(item["file_id"])
            Config.GET_FILE[item["id"]] = path

        while not os.path.exists(path):
            await asyncio.sleep(0.5)

        return path

    return await get_link(item["source"])


def _media_stream(link, item, seek=None):
    # Video mode: audio + video are sent to the Telegram video chat.
    if item.get("video", True):
        kwargs = {}
        if seek and seek.get("start", 0) > 0:
            kwargs["ffmpeg_parameters"] = f"-ss {float(seek['start'])}"

        return MediaStream(
            link,
            AudioQuality.HIGH,
            VideoQuality.HD_720p,
            **kwargs,
        )

    # Audio-only media remains supported for compatibility.
    kwargs = {"video_flags": MediaStream.Flags.IGNORE}
    if seek and seek.get("start", 0) > 0:
        kwargs["ffmpeg_parameters"] = f"-ss {float(seek['start'])}"

    return MediaStream(
        link,
        AudioQuality.HIGH,
        **kwargs,
    )


async def _start(item, replace=False, seek=None):
    from user import group_call

    link = await _resolve(item)

    if not link:
        return False, "Unable to resolve media URL."

    duration = 0
    if isinstance(link, str) and os.path.isfile(link):
        duration = await get_duration(link)

    try:
        stream = _media_stream(link, item, seek)
        # Modern PyTgCalls automatically creates the group call when needed
        # and replaces the current stream when play() is called again.
        await group_call.play(Config.CHAT, stream)

    except Exception as e:
        LOGGER.error("Stream start failed: %s", e, exc_info=True)
        return False, str(e)

    Config.CALL_STATUS = True
    Config.current = dict(
        item,
        resolved=link,
        duration=duration,
        started_at=time.time() - float((seek or {}).get("start", 0)),
    )
    Config.DATA["FILE_DATA"] = {"file": link, "dur": duration}
    return True, None


async def add_to_queue(item):
    item.setdefault("video", True)
    Config.playlist.append(item)

    if Config.current is None:
        await play_next()

    return True


async def play_next():
    if not Config.playlist:
        await leave_call()
        return False

    old = Config.current
    item = Config.playlist.pop(0)

    ok, error = await _start(item, replace=Config.CALL_STATUS)
    if not ok:
        LOGGER.error("Could not play %s: %s", item.get("title", "media"), error)
        Config.current = None
        return False

    if old and old.get("kind") == "telegram":
        old_path = Config.GET_FILE.pop(old["id"], None)
        if old_path and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    return True


async def stream_from_link(link, title="Live Stream"):
    item = {
        "id": f"stream-{time.time_ns()}",
        "title": title,
        "kind": "url",
        "source": link,
        "requested_by": "admin",
        "video": True,
    }

    Config.playlist.clear()
    return await _start(item, replace=Config.CALL_STATUS)


async def skip():
    current = Config.current

    if current and current.get("kind") == "telegram":
        path = Config.GET_FILE.pop(current["id"], None)
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    Config.current = None
    return await play_next()


async def leave_call():
    from user import group_call

    try:
        await group_call.leave_call(Config.CHAT)
    except Exception as e:
        LOGGER.warning("Leave failed: %s", e)

    Config.CALL_STATUS = False
    Config.PAUSE = False
    Config.MUTED = False
    Config.current = None


async def restart_playout():
    if not Config.current:
        return await play_next()

    item = Config.current.copy()
    item.pop("resolved", None)
    item.pop("duration", None)
    item.pop("started_at", None)

    return (await _start(item, replace=True))[0]


async def seek_file(offset):
    if not Config.current:
        return False, "Nothing is playing."

    duration = float(Config.current.get("duration") or 0)
    if duration <= 0:
        return False, "Seeking is unavailable for live streams."

    started = float(Config.current.get("started_at", time.time()))
    current_pos = max(0, time.time() - started)
    target = max(0, min(duration, current_pos + offset))

    if target >= duration:
        await skip()
        return True, None

    item = {
        k: v
        for k, v in Config.current.items()
        if k not in ("resolved", "duration", "started_at")
    }

    ok, error = await _start(
        item,
        replace=True,
        seek={"start": target},
    )

    return ok, error


async def pause():
    from user import group_call

    try:
        await group_call.pause(Config.CHAT)
        Config.PAUSE = True
        return True
    except Exception as e:
        LOGGER.error("Pause failed: %s", e)
        return False


async def resume():
    from user import group_call

    try:
        await group_call.resume(Config.CHAT)
        Config.PAUSE = False
        return True
    except Exception as e:
        LOGGER.error("Resume failed: %s", e)
        return False


async def volume(value):
    from user import group_call

    try:
        await group_call.change_volume_call(Config.CHAT, int(value))
        Config.VOLUME = int(value)
        return True
    except Exception as e:
        LOGGER.error("Volume change failed: %s", e)
        return False


async def mute():
    from user import group_call

    try:
        await group_call.mute(Config.CHAT)
        Config.MUTED = True
        return True
    except Exception as e:
        LOGGER.error("Mute failed: %s", e)
        return False


async def unmute():
    from user import group_call

    try:
        await group_call.unmute(Config.CHAT)
        Config.MUTED = False
        return True
    except Exception as e:
        LOGGER.error("Unmute failed: %s", e)
        return False


def _fmt(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def player_text():
    if not Config.current:
        return "⏹ Nothing is playing."

    duration = float(Config.current.get("duration") or 0)

    if duration <= 0:
        return f"▶️ <b>{Config.current['title']}</b>\n🔴 Live stream"

    elapsed = max(
        0,
        min(
            duration,
            time.time() - float(Config.current.get("started_at", time.time())),
        ),
    )

    return f"▶️ <b>{Config.current['title']}</b>\n⏱ {_fmt(elapsed)} / {_fmt(duration)}"


def queue_text():
    text = player_text()

    if Config.playlist:
        text += "\n\n<b>Queue</b>\n" + "\n".join(
            f"{i}. {x['title']}" for i, x in enumerate(Config.playlist, 1)
        )

    return text


async def media_from_message(message):
    reply = message.reply_to_message
    requester = message.from_user.mention if message.from_user else "Anonymous"

    if reply:
        media = reply.video or reply.audio or reply.document

        if media:
            mime = getattr(media, "mime_type", "") or ""

            if reply.document and not mime.startswith(("video/", "audio/")):
                return None, "Reply with a video or audio file."

            is_video = bool(reply.video or mime.startswith("video/"))

            return {
                "id": f"tg-{reply.chat.id}-{reply.id}",
                "title": (
                    getattr(media, "file_name", None)
                    or getattr(media, "title", None)
                    or "Telegram media"
                ),
                "kind": "telegram",
                "file_id": media.file_id,
                "requested_by": requester,
                "video": is_video,
            }, None

        if reply.text:
            source = reply.text.strip()
        else:
            return None, "Reply to media or send a URL."
    else:
        if len(message.command) < 2:
            return None, "Usage: /play <URL> or reply to Telegram media."

        source = " ".join(message.command[1:]).strip()

    if not re.match(r"^https?://", source):
        return None, "Only HTTP/HTTPS URLs are supported."

    title = source
    video = True

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, source, False)

        title = info.get("title") or source
        video = info.get("vcodec") not in (None, "none")
    except Exception:
        pass

    return {
        "id": f"url-{time.time_ns()}",
        "title": title,
        "kind": "url",
        "source": source,
        "requested_by": requester,
        "video": video,
    }, None
