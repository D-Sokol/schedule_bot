"""
This script crops/resizes user images as a separate microservice to avoid lags in bot responses.
"""

import asyncio
import io
import json
import logging
from asyncio import Event
from functools import partial
from typing import cast

from aiogram import Bot
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from PIL import Image
from nats.js.object_store import ObjectStore


BUCKET_NAME = "assets"
CONVERT_RAW_SUBJECT_NAME = "assets.convert.raw"
CONVERT_FILE_ID_SUBJECT_NAME = "assets.convert.file_id"
IMAGE_FORMAT = "png"

SAVE_NAME_HEADER = "Sch-Save-Name"
RESIZE_MODE_HEADER = "Sch-Resize-Mode"
TARGET_SIZE_HEADER = "Sch-Target-Size"

logger = logging.getLogger(__name__)


async def convert_image(
    image: Image.Image, store: ObjectStore, resize_mode: str, save_name: str, target_size: tuple[int, int]
) -> None:
    stream = io.BytesIO()
    target_w, target_h = target_size
    if resize_mode == "ignore":
        image.save(stream, format=IMAGE_FORMAT)
    elif resize_mode == "crop":
        image = image.crop((0, 0, target_w, target_h))  # (x1, y1, x2, y2), >image.size = black
        image.save(stream, format=IMAGE_FORMAT)
    elif resize_mode == "resize":
        image = image.resize((target_w, target_h))
        image.save(stream, format=IMAGE_FORMAT)
    else:
        raise ValueError(f"Unknown resize mode: {resize_mode}")

    logging.debug("Converted %s", save_name)
    await store.put(save_name, stream.getvalue())


async def convert_raw_handler(msg: Msg, store: ObjectStore) -> None:
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    save_name = msg.headers[SAVE_NAME_HEADER]
    resize_mode = msg.headers[RESIZE_MODE_HEADER]
    target_w, target_h = cast(list[int], json.loads(msg.headers[TARGET_SIZE_HEADER]))

    logger.info("Converting %s with mode %s", save_name, resize_mode)

    image: Image.Image = Image.open(io.BytesIO(msg.data), formats=[IMAGE_FORMAT])
    await convert_image(image, store, resize_mode, save_name, target_size=(target_w, target_h))
    await msg.ack()


async def convert_file_id_handler(msg: Msg, store: ObjectStore, bot: Bot) -> None:
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    save_name = msg.headers[SAVE_NAME_HEADER]
    resize_mode = msg.headers[RESIZE_MODE_HEADER]
    target_w, target_h = cast(list[int], json.loads(msg.headers[TARGET_SIZE_HEADER]))

    logger.info("Converting %s with mode %s", save_name, resize_mode)

    file_id = msg.data.decode()
    file = await bot.download(file_id)
    assert file is not None, "image loaded to file system"
    image = Image.open(file)

    await convert_image(image, store, resize_mode, save_name, target_size=(target_w, target_h))
    await msg.ack()


async def convert_loop(js: JetStreamContext, bot: Bot, shutdown_event: asyncio.Event | None = None):
    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(
        CONVERT_RAW_SUBJECT_NAME,
        cb=partial(convert_raw_handler, store=store),
        durable="converter_raw",
        manual_ack=True,
    )
    await js.subscribe(
        CONVERT_FILE_ID_SUBJECT_NAME,
        cb=partial(convert_file_id_handler, store=store, bot=bot),
        durable="converter_file_id",
        manual_ack=True,
    )
    logger.info("Connected to NATS")

    if shutdown_event is None:
        shutdown_event = Event()

    try:
        assert shutdown_event is not None
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.debug("Main task was cancelled")
    logger.warning("Exiting main task")
