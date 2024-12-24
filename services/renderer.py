"""
This script renders a final schedule as a separate microservice to avoid lags in bot responses.
"""
import asyncio
import io
import json
import logging
import os
from asyncio import Event

import nats
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from PIL import Image


BUCKET_NAME = "assets"
INPUT_SUBJECT_NAME = "schedules.request"
OUTPUT_SUBJECT_NAME = "schedules.ready"
IMAGE_FORMAT = "png"

USER_ID_HEADER = "Sch-User-Id"
CHAT_ID_HEADER = "Sch-Chat-Id"
ELEMENT_NAME_HEADER = "Sch-Element-Name"

logger = logging.getLogger(__name__)


async def render_loop(js: JetStreamContext, shutdown_event: asyncio.Event | None = None):
    async def callback(msg: Msg):
        user_id = msg.headers[USER_ID_HEADER]
        chat_id = msg.headers[CHAT_ID_HEADER]
        element_name = msg.headers[ELEMENT_NAME_HEADER]

        payload = json.loads(msg.data.decode())

        logger.info("Converting %s for %s with payload %s", element_name, user_id, payload)
        background_data = await store.get(element_name)
        background = Image.open(io.BytesIO(background_data.data), formats=[IMAGE_FORMAT])

        # TODO: edit wrt template
        stream = io.BytesIO()
        background.save(stream, format=IMAGE_FORMAT)

        logging.debug("Created schedule for %s", user_id)
        await js.publish(
            subject=OUTPUT_SUBJECT_NAME,
            payload=stream.getvalue(),
            headers={
                USER_ID_HEADER: user_id,
                CHAT_ID_HEADER: chat_id,
            },
        )
        await msg.ack()

    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(INPUT_SUBJECT_NAME, cb=callback, durable="renderer", manual_ack=True)
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
    await render_loop(js)
    await nc.close()


if __name__ == '__main__':
    nats_servers_ = os.getenv("NATS_SERVERS")
    asyncio.run(main(nats_servers_))
