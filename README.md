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

This project is intended to run with the Dockerfile because the bot requires FFmpeg and the legacy PyTgCalls 0.8.6 runtime.

```bash
docker build -t watchparty .
docker run --env-file .env watchparty
```

## Koyeb

Use **Docker** as the Builder for the Koyeb Service. Do not use the Python Buildpack for this project: the Dockerfile installs FFmpeg and pins the runtime to Python 3.10 for compatibility with PyTgCalls 0.8.6.

Koyeb settings:

- Source: GitHub → `theandroidlord/WatchParty-bot`
- Branch: `main`
- Builder: **Dockerfile**
- Dockerfile: `Dockerfile`
- Service type: **Web Service**
- Exposed port: `8000` / HTTP
- Route: `/` → port `8000`
- Health check: `/health` on port `8000`
- Scaling: 1 instance

The application reads Koyeb's `PORT` environment variable automatically and falls back to `8000` for local/Docker runs.

Required Koyeb environment variables: `API_ID`, `API_HASH`, `BOT_TOKEN`, `SESSION_STRING`, `CHAT`.

Optional: `ADMINS`, `QUALITY`, `BITRATE`, `FPS`.
