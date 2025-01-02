"""
This script renders a final schedule as a separate microservice to avoid lags in bot responses.
"""
import asyncio
import io
import logging
import os
from asyncio import Event
from contextlib import nullcontext
from datetime import date
from functools import partial

import msgpack
import nats
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.object_store import ObjectStore
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from services.renderer.templates import Template
from services.renderer.weekdays import Schedule

BUCKET_NAME = "assets"
INPUT_SUBJECT_NAME = "schedules.request"
OUTPUT_SUBJECT_NAME = "schedules.ready"
IMAGE_FORMAT = "png"

USER_ID_HEADER = "Sch-User-Id"
CHAT_ID_HEADER = "Sch-Chat-Id"
START_DATE_HEADER = "Sch-Start-Date"
ELEMENT_NAME_HEADER = "Sch-Element-Name"

logger = logging.getLogger(__name__)


async def render(msg: Msg, js: JetStreamContext, store: ObjectStore, session_pool: async_sessionmaker | None = None):
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    user_id = msg.headers[USER_ID_HEADER]
    chat_id = msg.headers[CHAT_ID_HEADER]
    element_name = msg.headers[ELEMENT_NAME_HEADER]
    start_date = date.fromisoformat(msg.headers[START_DATE_HEADER])

    logger.debug("Trying to parse objects")
    template_dict, schedule_dict = msgpack.unpackb(msg.data)
    template = Template.model_validate(template_dict)
    schedule = Schedule.model_validate(schedule_dict)
    logger.debug("Template and schedule successfully parsed")

    logger.info("Converting %s for %s", element_name, user_id)
    background_data = await store.get(element_name)
    if background_data.data is None:
        logger.error("No content in image %s.%s", user_id, element_name)
        raise ValueError("No content in image")
    # If background has an alpha channel, pasting an RGBA patches produces an unexpected transparency.
    # Now partially transparent background is not supported, see also :func:`PIL.Image.alpha_composite` .
    background = Image.open(io.BytesIO(background_data.data), formats=[IMAGE_FORMAT]).convert(mode="RGB")
    draw = ImageDraw.ImageDraw(background, mode="RGBA")

    async with (session_pool or nullcontext)() as session:
        await template.apply(background, draw, start_date, schedule, store=store, session=session)

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


async def render_loop(
        js: JetStreamContext,
        session_pool: async_sessionmaker | None = None,
        shutdown_event: asyncio.Event | None = None
):
    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(
        INPUT_SUBJECT_NAME,
        cb=partial(render, js=js, store=store, session_pool=session_pool),
        durable="renderer",
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


async def main(servers: str = "nats://localhost:4222", db_url: str | None = None):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    if db_url:
        engine = create_async_engine(db_url, echo=False)
        session_pool = async_sessionmaker(engine, expire_on_commit=False)
    else:
        session_pool = None
    await render_loop(js, session_pool)
    await nc.close()


if __name__ == '__main__':
    nats_servers_ = os.getenv("NATS_SERVERS")
    database_url = os.getenv("DB_URL")
    if nats_servers_ is None:
        logger.critical("Cannot run without nats url")
        exit(1)
    if database_url is None:
        logger.warning("Loading images via name is not possible")
    asyncio.run(main(nats_servers_, database_url))