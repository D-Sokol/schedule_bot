"""
This script crops/resizes user images as a separate microservice to avoid lags in bot responses.
"""
import asyncio
import io
import json
import logging
import os
from asyncio import Event
from typing import cast

import nats
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from PIL import Image


BUCKET_NAME = "assets"
CONVERT_SUBJECT_NAME = "assets.convert"
IMAGE_FORMAT = "png"

SAVE_NAME_HEADER = "Sch-Save-Name"
RESIZE_MODE_HEADER = "Sch-Resize-Mode"
TARGET_SIZE_HEADER = "Sch-Target-Size"

logger = logging.getLogger(__name__)


async def convert_loop(js: JetStreamContext, shutdown_event: asyncio.Event | None = None):
    async def callback(msg: Msg):
        save_name = msg.headers.get(SAVE_NAME_HEADER)
        resize_mode = msg.headers.get(RESIZE_MODE_HEADER)
        target_w, target_h = cast(list[int], json.loads(msg.headers.get(TARGET_SIZE_HEADER)))

        logger.info("Converting %s with mode %s", save_name, resize_mode)

        image = Image.open(io.BytesIO(msg.data), formats=[IMAGE_FORMAT])
        stream = io.BytesIO()
        if resize_mode == "ignore":
            stream.write(msg.data)
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
        await msg.ack()

    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(CONVERT_SUBJECT_NAME, cb=callback, durable="converter", manual_ack=True)
    logger.info("Connected to NATS")

    if shutdown_event is None:
        shutdown_event = Event()

    try:
        assert shutdown_event is not None
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.debug("Main task was cancelled")
    logger.warning("Exiting main task")


async def main(servers: str = "nats://localhost:4222"):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    await convert_loop(js)
    await nc.close()


if __name__ == '__main__':
    nats_servers_ = os.getenv("NATS_SERVERS")
    asyncio.run(main(nats_servers_))
