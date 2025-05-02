import asyncio
import os

import nats
from nats.js.api import ObjectStoreConfig, StorageType, StreamConfig, RetentionPolicy


async def upgrade(servers: str):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()

    await js.create_object_store(
        "assets",
        config=ObjectStoreConfig(
            description="Images for scheduler bot, both backgrounds and patches",
            storage=StorageType.FILE,
        ),
    )
    await js.create_object_store(
        "rendered",
        config=ObjectStoreConfig(
            description="Stores rendered schedules before sending them to the user",
            ttl=4 * 3600,
            storage=StorageType.MEMORY,
        ),
    )
    await js.add_stream(
        StreamConfig(
            name="Assets-queue",
            description="Working queue for cropping/resizing images",
            subjects=["assets.>"],
            retention=RetentionPolicy.WORK_QUEUE,
            max_age=3600,
            max_msg_size=10 * 1024 * 1024,
        )
    )
    await js.add_stream(
        StreamConfig(
            name="Schedules-queue",
            description="Working queue for rendering schedules",
            subjects=["schedules.>"],
            retention=RetentionPolicy.WORK_QUEUE,
            max_age=3600,
            max_msg_size=10 * 1024 * 1024,
        )
    )


async def downgrade(servers: str):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()

    await js.delete_object_store("assets")
    # `rendered` object store does not persist anyway.
    await js.delete_stream("Assets-queue")
    await js.delete_stream("Schedules-queue")


if __name__ == "__main__":
    nats_servers = os.getenv("NATS_SERVERS")
    if nats_servers is None:
        exit(1)
    asyncio.run(upgrade(nats_servers))
