#!/usr/bin/env python3
import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pyrogram import idle
from pyrogram.errors import FloodWait

from bot import bot
from config import Config
from user import USER, group_call
from utils import LOGGER, startup_check


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/health/"):
            if getattr(Config, "IS_READY", False):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"WatchParty bot is running")
            else:
                self.send_response(503)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                msg = Config.STARTUP_ERROR or "WatchParty bot is initializing or failed."
                self.wfile.write(msg.encode("utf-8"))
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


async def start_bot_with_retry():
    while True:
        try:
            await bot.start()
            return
        except FloodWait as e:
            wait_seconds = int(getattr(e, "value", 0) or 0) + 5
            LOGGER.warning(
                "Telegram FloodWait during bot authorization. "
                "Waiting %s seconds before retrying.",
                wait_seconds,
            )

            if bot.is_connected:
                try:
                    await bot.disconnect()
                except Exception:
                    LOGGER.exception("Failed to disconnect bot after FloodWait")

            await asyncio.sleep(wait_seconds)


async def main():
    health_server = start_health_server()

    try:
        await start_bot_with_retry()
        Config.BOT_USERNAME = (await bot.get_me()).username

        # PyTgCalls starts the user client; only query the user session after it is ready.
        await group_call.start()
        # Register PyTgCalls event handlers only after group_call has been created.
        import userplugins.group_call  # noqa: F401
        Config.USER_ID = (await USER.get_me()).id

        if not await startup_check():
            LOGGER.error("Startup checks failed. Bot will stay idle to prevent rapid restart loops.")
            await idle()
            return

        Config.IS_READY = True
        LOGGER.info("%s started.", Config.BOT_USERNAME)

        await idle()
    except Exception as e:
        LOGGER.exception("Startup failed with exception: %s", e)
        # Stay idle to prevent rapid restart loops on Koyeb
        await idle()
    finally:
        try:
            await group_call.stop()
        except Exception:
            LOGGER.exception("Failed to stop PyTgCalls")

        if bot.is_connected:
            try:
                await bot.stop()
            except Exception:
                LOGGER.exception("Failed to stop bot")

        if USER.is_connected:
            try:
                await USER.stop()
            except Exception:
                LOGGER.exception("Failed to stop user session")

        health_server.shutdown()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
