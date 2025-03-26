import asyncio
import logging
from asyncio import Event
from functools import partial

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile
from nats.aio.msg import Msg
from nats.js import JetStreamContext


INPUT_SUBJECT_NAME = "schedules.ready"
INPUT_SUBJECT_ERROR = "schedules.error"
IMAGE_FORMAT = "png"

USER_ID_HEADER = "Sch-User-Id"
CHAT_ID_HEADER = "Sch-Chat-Id"

logger = logging.getLogger(__name__)


async def send(msg: Msg, bot: Bot, filename="Schedule.png") -> None:
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    chat_id = int(msg.headers[CHAT_ID_HEADER])
    try:
        await bot.send_document(
            chat_id=chat_id,
            document=BufferedInputFile(file=msg.data, filename=filename),
        )
        await msg.ack()
    except TelegramRetryAfter as e:
        await msg.nak(e.retry_after)


async def response_error(msg: Msg, bot: Bot) -> None:
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    chat_id = int(msg.headers[CHAT_ID_HEADER])
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg.data.decode(),
        )
        await msg.ack()
    except TelegramRetryAfter as e:
        await msg.nak(e.retry_after)


async def sender_loop(js: JetStreamContext, bot: Bot, shutdown_event: asyncio.Event | None = None):
    await js.subscribe(INPUT_SUBJECT_NAME, cb=partial(send, bot=bot), durable="sender", manual_ack=True)
    await js.subscribe(INPUT_SUBJECT_ERROR, cb=partial(response_error, bot=bot), durable="sender_err", manual_ack=True)
    logger.info("Connected to NATS")

    if shutdown_event is None:
        shutdown_event = Event()

    try:
        assert shutdown_event is not None
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.debug("Main task was cancelled")
    logger.warning("Exiting main task")
