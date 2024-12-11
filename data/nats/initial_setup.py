import asyncio
import os

import nats
from nats.js.api import ObjectStoreConfig, StorageType


async def upgrade(servers: str):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()

    await js.create_object_store("assets", config=ObjectStoreConfig(
        description="Images for scheduler bot, both backgrounds and patches",
        storage=StorageType.MEMORY,
    ))


async def downgrade(servers: str):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()

    await js.delete_object_store("assets")


if __name__ == '__main__':
    nats_servers = os.getenv("NATS_SERVERS")
    if nats_servers is None:
        exit(1)
    asyncio.run(upgrade(nats_servers))
