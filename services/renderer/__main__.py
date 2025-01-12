import asyncio
import logging
import os

import nats
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from . import render_loop


logger = logging.getLogger(__name__)

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
