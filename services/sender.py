import asyncio
import logging
import os
from asyncio import Event
from functools import partial

import nats
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BufferedInputFile
from nats.aio.msg import Msg
from nats.js import JetStreamContext


INPUT_SUBJECT_NAME = "schedules.ready"
IMAGE_FORMAT = "png"

USER_ID_HEADER = "Sch-User-Id"
CHAT_ID_HEADER = "Sch-Chat-Id"

logger = logging.getLogger(__name__)


async def send(msg: Msg, bot: Bot, filename="Schedule.png") -> None:
    chat_id = int(msg.headers[CHAT_ID_HEADER])
    await bot.send_document(
        chat_id=chat_id,
        document=BufferedInputFile(file=msg.data, filename=filename),
    )
    await msg.ack()


async def sender_loop(js: JetStreamContext, bot: Bot, shutdown_event: asyncio.Event | None = None):
    await js.subscribe(INPUT_SUBJECT_NAME, cb=partial(send, bot=bot), durable="sender", manual_ack=True)
    logger.info("Connected to NATS")

    if shutdown_event is None:
        shutdown_event = Event()

    try:
        assert shutdown_event is not None
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.debug("Main task was cancelled")
    logger.warning("Exiting main task")


async def main(token: str, servers: str = "nats://localhost:4222"):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    await sender_loop(js, bot)
    await nc.close()


if __name__ == '__main__':
    bot_token = os.getenv("TOKEN")
    nats_servers_ = os.getenv("NATS_SERVERS")
    asyncio.run(main(bot_token, nats_servers_))
