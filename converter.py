"""
This script crops/resizes user images as a separate microservice to avoid lags in bot responses.
"""
import asyncio
import json
import os

import nats
from nats.aio.msg import Msg
from nats.js import JetStreamContext

BUCKET_NAME = "assets"
CONVERT_SUBJECT_NAME = "assets.convert"

SAVE_NAME_HEADER = "Sch-Save-Name"
RESIZE_MODE_HEADER = "Sch-Resize-Mode"
TARGET_SIZE_HEADER = "Sch-Target-Size"


async def convert(js: JetStreamContext):
    async def callback(msg: Msg):
        save_name = msg.headers.get(SAVE_NAME_HEADER)
        resize_mode = msg.headers.get(RESIZE_MODE_HEADER)
        _target_size: list[int] = json.loads(msg.headers.get(TARGET_SIZE_HEADER))
        if resize_mode not in {"resize", "crop", "ignore"}:
            raise ValueError(f"Unknown resize mode: {resize_mode}")

        # TODO: actually convert image.
        await store.put(save_name, msg.data)
        await msg.ack()

    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(CONVERT_SUBJECT_NAME, cb=callback, durable="converter", manual_ack=True)

    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass


async def main(servers: str = "nats://localhost:4222"):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    await convert(js)
    await nc.close()


if __name__ == '__main__':
    nats_servers_ = os.getenv("NATS_SERVERS")
    asyncio.run(main())
