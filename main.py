#!/usr/bin/env python3
import asyncio
from pyrogram import idle
from bot import bot
from config import Config
from user import USER, group_call
from utils import LOGGER, startup_check

async def main():
    await bot.start()
    Config.BOT_USERNAME = (await bot.get_me()).username
    Config.USER_ID = (await USER.get_me()).id

    if not await startup_check():
        await bot.stop()
        await USER.stop()
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

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
