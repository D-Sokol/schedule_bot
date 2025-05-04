import asyncio
import logging
from asyncio import Event
from functools import partial

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import ObjectStoreConfig, StorageType
from nats.js.object_store import ObjectStore

RESULT_BUCKET_NAME = "rendered"

INPUT_RAW_SUBJECT_NAME = "schedules.ready"
INPUT_STORE_SUBJECT_NAME = "schedules.ready_store"
INPUT_SUBJECT_ERROR = "schedules.error"
IMAGE_FORMAT = "png"

USER_ID_HEADER = "Sch-User-Id"
CHAT_ID_HEADER = "Sch-Chat-Id"

logger = logging.getLogger(__name__)


async def send_raw(msg: Msg, bot: Bot, filename="Schedule.png") -> None:
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


async def send_from_store(msg: Msg, bot: Bot, store: ObjectStore, filename="Schedule.png") -> None:
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    chat_id = int(msg.headers[CHAT_ID_HEADER])
    rendered_name = msg.data.decode()
    result = await store.get(rendered_name)

    try:
        await bot.send_document(
            chat_id=chat_id,
            document=BufferedInputFile(file=result.data, filename=filename),
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
    await js.create_object_store(
        "rendered",
        config=ObjectStoreConfig(
            description="Stores rendered schedules before sending them to the user",
            ttl=4 * 3600,
            storage=StorageType.MEMORY,
        ),
    )
    store = await js.object_store(RESULT_BUCKET_NAME)
    await js.subscribe(INPUT_RAW_SUBJECT_NAME, cb=partial(send_raw, bot=bot), durable="sender", manual_ack=True)
    await js.subscribe(
        INPUT_STORE_SUBJECT_NAME,
        cb=partial(send_from_store, bot=bot, store=store),
        durable="sender_store",
        manual_ack=True,
    )
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
