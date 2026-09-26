# WatchParty

Minimal Telegram bot for streaming media into a Telegram group voice/video chat.

## Features

- Telegram video/audio media playback
- YouTube and other yt-dlp-supported URLs
- Direct HTTP/HTTPS media URLs
- Live/direct streaming with `/stream`
- Queue playback
- Pause/resume, skip, replay, seek
- Volume and mute/unmute controls
- Leave the video chat
- Automatically advances through the queue

## Removed

Recording, scheduling, playlist import/export, channel crawling, inline mode, database-backed state, runtime Heroku configuration, admin promotion, and the old callback/settings framework.

## Environment

Required: `API_ID`, `API_HASH`, `BOT_TOKEN`, `SESSION_STRING`, `CHAT`.

Optional: `ADMINS`, `QUALITY`, `BITRATE`, `FPS`.

## Commands

`/play <URL>` or reply to Telegram media with `/play`  
`/stream <URL>`  
`/player`  
`/skip`  
`/replay`  
`/seek <seconds>`  
`/pause` / `/resume`  
`/volume <1-200>`  
`/vcmute` / `/vcunmute`  
`/leave`

The user account represented by `SESSION_STRING` must be a member of the target chat and should have permission to manage the voice/video chat. The bot should also be present in the target chat.

## Local setup

Install FFmpeg, then:

```bash
pip install -r requirements.txt
python3 main.py
```

## Docker

```bash
docker build -t watchparty .
docker run --env-file .env watchparty
```
