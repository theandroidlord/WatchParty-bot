# WatchParty Bot

Minimal Telegram video-chat streaming bot using current PyTgCalls + NTgCalls.

## Commands

- /join — join the existing video chat
- /play <URL> — download and play a video
- /pause — pause playback
- /leave — leave the video chat

## Environment

Copy env.sample to .env and set:

- API_ID
- API_HASH
- BOT_TOKEN
- SESSION_STRING
- CHAT_ID
- ADMINS

If ADMINS is empty, commands are allowed for anyone in CHAT_ID.

## Koyeb

Use the Dockerfile. No Node.js installation is required.

The bot downloads the selected video with yt-dlp, displays a live progress bar, then feeds the local MP4 directly to PyTgCalls as audio + 720p video.

PyTgCalls/NTgCalls provides the Telegram call transport.
