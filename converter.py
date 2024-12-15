"""
This script crops/resizes user images as a separate microservice to avoid lags in bot responses.
"""
import asyncio
import json
import logging
import os
import signal
from asyncio import Event
from contextlib import suppress

import nats
from nats.aio.msg import Msg
from nats.js import JetStreamContext

BUCKET_NAME = "assets"
CONVERT_SUBJECT_NAME = "assets.convert"

SAVE_NAME_HEADER = "Sch-Save-Name"
RESIZE_MODE_HEADER = "Sch-Resize-Mode"
TARGET_SIZE_HEADER = "Sch-Target-Size"

logger = logging.getLogger(__name__)


def _set_event(event: Event, _handler: asyncio.events.Handle | None = None) -> None:
    logger.info("Received signal, stopping converting...")
    if _handler is not None:
        _handler._run()  # noqa
    event.set()


async def _set_signals(event: Event):
    loop = asyncio.get_running_loop()
    with suppress(NotImplementedError, TypeError, AttributeError):
        for sig in (signal.SIGTERM, signal.SIGINT):
            # asyncio loop does not provide way to get current handler or add another one without removing it.
            # Since aiogram set its own handlers to properly stop polling, we have to extract it and run both of them.
            prev_handler: asyncio.events.Handle | None = loop._signal_handlers.get(sig)  # noqa
            loop.add_signal_handler(sig, _set_event, event, prev_handler)


async def convert(js: JetStreamContext, handle_signals: bool = True):
    async def callback(msg: Msg):
        save_name = msg.headers.get(SAVE_NAME_HEADER)
        resize_mode = msg.headers.get(RESIZE_MODE_HEADER)
        _target_size: list[int] = json.loads(msg.headers.get(TARGET_SIZE_HEADER))
        if resize_mode not in {"resize", "crop", "ignore"}:
            raise ValueError(f"Unknown resize mode: {resize_mode}")

        logger.info("Converting %s with mode %s", save_name, resize_mode)

        # TODO: actually convert image.
        await store.put(save_name, msg.data)
        await msg.ack()

    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(CONVERT_SUBJECT_NAME, cb=callback, durable="converter", manual_ack=True)
    logger.info("Connected to NATS")

    shutdown_event = Event()
    if handle_signals:
        logger.debug("Manage signal handlers")
        await _set_signals(shutdown_event)

    try:
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.debug("Main task was cancelled")
    logger.warning("Exiting main task")


async def main(servers: str = "nats://localhost:4222"):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    await convert(js)
    await nc.close()


if __name__ == '__main__':
    nats_servers_ = os.getenv("NATS_SERVERS")
    asyncio.run(main())
