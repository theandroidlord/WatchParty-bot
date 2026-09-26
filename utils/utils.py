import asyncio, json, os, random, re, time
from math import gcd

import yt_dlp
from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, ChannelInvalid
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import CreateGroupCall
from pyrogram.types import Message
from pytgcalls import StreamType
from pytgcalls.exceptions import GroupCallNotFound, InvalidVideoProportion
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped, AudioParameters, VideoParameters

from bot import bot
from config import Config
from user import USER, group_call
from .logger import LOGGER
from .pyro_dl import Downloader

dl = Downloader()


async def get_admins(chat_id):
    ids = set(Config.ADMINS)
    try:
        async for member in bot.get_chat_members(chat_id, filter="administrators"):
            ids.add(member.user.id)
    except Exception as e:
        LOGGER.warning("Could not load chat admins: %s", e)
    return list(ids)


async def is_admin(_, client, message: Message):
    if message.from_user is None:
        return bool(message.sender_chat)
    return message.from_user.id in await get_admins(Config.CHAT)


async def valid_chat(_, client, message: Message):
    return message.chat.type == "private" or message.chat.id == Config.CHAT


chat_filter = filters.create(valid_chat)
admin_filter = filters.create(is_admin)


def is_ytdl_supported(url):
    try:
        return any(x.suitable(url) and x.IE_NAME != "generic" for x in yt_dlp.extractor.gen_extractors())
    except Exception:
        return False


async def get_link(url):
    if not is_ytdl_supported(url):
        return url
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "--geo-bypass", "-g",
        "-f", "best[height<=?720][width<=?1280]/best", url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0 or not out:
        LOGGER.error("yt-dlp failed: %s", err.decode(errors="ignore"))
        return None
    return out.decode().strip().splitlines()[-1]


async def is_audio(path):
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-of", "json", "-show_streams", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    try:
        return any(s.get("codec_type") == "audio" for s in json.loads(out.decode()).get("streams", []))
    except Exception:
        return False


async def get_height_and_width(path):
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    try:
        streams = json.loads(out.decode()).get("streams", [])
        if not streams:
            return None, None
        return streams[0].get("width"), streams[0].get("height")
    except Exception:
        return None, None


async def get_duration(path):
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    try:
        value = json.loads(out.decode()).get("format", {}).get("duration")
        return float(value) if value else 0
    except Exception:
        return 0


def resize_ratio(width, height):
    if not width or not height:
        return 2, 2
    if width > height:
        scale = (min(width, 1280) * 100) / width
    else:
        scale = (min(height, 720) * 100) / height
    width = round(width * scale / 100)
    height = round(height * scale / 100)
    d = gcd(width, height)
    width, height = round(width / d * d), round(height / d * d)
    return (width - width % 2 or 2), (height - height % 2 or 2)


async def startup_check():
    required = {
        "API_ID": Config.API_ID, "API_HASH": Config.API_HASH,
        "BOT_TOKEN": Config.BOT_TOKEN, "SESSION_STRING": Config.SESSION,
        "CHAT": Config.CHAT,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        Config.STARTUP_ERROR = "Missing: " + ", ".join(missing)
        LOGGER.error(Config.STARTUP_ERROR)
        return False
    try:
        member = await USER.get_chat_member(Config.CHAT, Config.USER_ID)
        if getattr(member, "status", None) not in ("administrator", "creator"):
            LOGGER.warning("The user session is not a chat administrator.")
    except (ValueError, PeerIdInvalid, ChannelInvalid):
        Config.STARTUP_ERROR = "The user session is not a member of CHAT."
        LOGGER.error(Config.STARTUP_ERROR)
        return False
    except Exception as e:
        LOGGER.error("CHAT validation failed: %s", e)
        return False
    return True


async def _ensure_call():
    try:
        result = await bot.send(GetFullChannel(channel=await bot.resolve_peer(Config.CHAT)))
        if result.full_chat.call is not None:
            return True
    except Exception as e:
        LOGGER.warning("Could not inspect active video chat: %s", e)
    try:
        await USER.send(CreateGroupCall(
            peer=await USER.resolve_peer(Config.CHAT),
            random_id=random.randint(10000, 999999999),
        ))
        await asyncio.sleep(2)
        return True
    except Exception as e:
        LOGGER.error("Could not create video chat: %s", e)
        return False


def _stream(link, width, height, seek=None):
    if width and height:
        width, height = resize_ratio(width, height)
        kwargs = {
            "video_parameters": VideoParameters(width, height, Config.FPS),
            "audio_parameters": AudioParameters(Config.BITRATE),
        }
        if seek:
            kwargs["additional_ffmpeg_parameters"] = f"-ss {seek['start']} -t {max(0, seek['end'])}"
        return AudioVideoPiped(link, **kwargs)
    kwargs = {"audio_parameters": AudioParameters(Config.BITRATE)}
    if seek:
        kwargs["additional_ffmpeg_parameters"] = f"-ss {seek['start']} -t {max(0, seek['end'])}"
    return AudioPiped(link, **kwargs)


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


async def _start(item, replace=False, seek=None):
    link = await _resolve(item)
    if not link:
        return False, "Unable to resolve media URL."
    audio = await is_audio(link)
    if not audio:
        return False, "The media has no playable audio track."
    width, height = await get_height_and_width(link)
    duration = await get_duration(link)
    if not await _ensure_call():
        return False, "Unable to create or find the video chat."
    stream = _stream(link, width, height, seek)
    try:
        if Config.CALL_STATUS and replace:
            await group_call.change_stream(Config.CHAT, stream)
        else:
            await group_call.join_group_call(
                Config.CHAT, stream, stream_type=StreamType().pulse_stream
            )
    except InvalidVideoProportion:
        return False, "Unsupported video dimensions."
    except Exception as e:
        LOGGER.error("Stream start failed: %s", e, exc_info=True)
        return False, str(e)
    Config.CALL_STATUS = True
    Config.current = dict(item, resolved=link, width=width, height=height,
                          duration=duration, started_at=time.time())
    Config.DATA["FILE_DATA"] = {"file": link, "dur": duration}
    return True, None


async def add_to_queue(item):
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
        LOGGER.error("Could not play %s: %s", item["title"], error)
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
    try:
        await group_call.leave_group_call(Config.CHAT)
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
    return (await _start(item, replace=Config.CALL_STATUS))[0]


async def seek_file(offset):
    if not Config.current:
        return False, "Nothing is playing."
    duration = float(Config.current.get("duration") or 0)
    if duration <= 0:
        return False, "Live streams cannot be seeked."
    started = float(Config.current.get("started_at", time.time()))
    current_pos = max(0, time.time() - started)
    target = max(0, min(duration, current_pos + offset))
    remaining = duration - target
    if remaining <= 0:
        await skip()
        return True, None
    item = {k: v for k, v in Config.current.items() if k not in ("resolved", "width", "height", "duration", "started_at")}
    item["source"] = Config.current["resolved"]
    ok, error = await _start(item, replace=True, seek={"start": target, "end": remaining})
    if ok:
        Config.current["started_at"] = time.time() - target
    return ok, error


async def pause():
    try:
        await group_call.pause_stream(Config.CHAT)
        Config.PAUSE = True
        return True
    except GroupCallNotFound:
        return False


async def resume():
    try:
        await group_call.resume_stream(Config.CHAT)
        Config.PAUSE = False
        return True
    except GroupCallNotFound:
        return False


async def volume(value):
    try:
        await group_call.change_volume_call(Config.CHAT, int(value))
        Config.VOLUME = int(value)
        return True
    except Exception as e:
        LOGGER.error("Volume change failed: %s", e)
        return False


async def mute():
    try:
        await group_call.mute_stream(Config.CHAT)
        Config.MUTED = True
        return True
    except Exception:
        return False


async def unmute():
    try:
        await group_call.unmute_stream(Config.CHAT)
        Config.MUTED = False
        return True
    except Exception:
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
    elapsed = max(0, time.time() - float(Config.current.get("started_at", time.time())))
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
            return {
                "id": f"tg-{reply.chat.id}-{reply.id}",
                "title": getattr(media, "file_name", None) or getattr(media, "title", None) or "Telegram media",
                "kind": "telegram",
                "file_id": media.file_id,
                "requested_by": requester,
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
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, source, False)
        title = info.get("title") or source
    except Exception:
        pass
    return {
        "id": f"url-{time.time_ns()}",
        "title": title,
        "kind": "url",
        "source": source,
        "requested_by": requester,
    }, None
