import asyncio
import logging
import os

import nats
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from . import convert_loop


logger = logging.getLogger(__name__)


async def main(token: str, servers: str = "nats://localhost:4222"):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    await convert_loop(js, bot)
    await nc.close()


if __name__ == "__main__":
    bot_token = os.getenv("TOKEN")
    nats_servers_ = os.getenv("NATS_SERVERS")
    if bot_token is None:
        logger.critical("Cannot run without bot token")
        exit(1)
    if nats_servers_ is None:
        logger.critical("Cannot run without nats url")
        exit(1)
    asyncio.run(main(bot_token, nats_servers_))
