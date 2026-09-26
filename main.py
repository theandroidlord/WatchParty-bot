#!/usr/bin/env python3
import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pyrogram import idle
from bot import bot
from config import Config
from user import USER, group_call
from utils import LOGGER, startup_check


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/health/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"WatchParty bot is running")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    LOGGER.info("Koyeb health server listening on port %s", port)
    return server


async def main():
    health_server = start_health_server()

    await bot.start()
    Config.BOT_USERNAME = (await bot.get_me()).username
    Config.USER_ID = (await USER.get_me()).id

    if not await startup_check():
        await bot.stop()
        await USER.stop()
        health_server.shutdown()
        return

    await group_call.start()
    LOGGER.info("%s started.", Config.BOT_USERNAME)

    try:
        await idle()
    finally:
        await group_call.stop()
        await bot.stop()
        if USER.is_connected:
            await USER.stop()
        health_server.shutdown()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
