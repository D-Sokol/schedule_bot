import argparse
import asyncio
import logging
import os
from pathlib import Path
from uuid import UUID

import nats
from nats.js.errors import ObjectNotFoundError
from nats.js.object_store import ObjectStore
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database_models import ImageAsset


BUCKET_NAME = "assets"


async def ensure_loaded(file_path: Path, store: ObjectStore, session: AsyncSession):
    if file_path.suffix.lower() != ".png":
        logging.warning("Only PNG format is supported, file %s may be inaccessible", file_path.name)

    result = await session.execute(
        text("SELECT element_id FROM elements WHERE user_id IS NULL AND name = :name LIMIT 1"),
        {"name": file_path.stem},
    )
    element_uuid: UUID | None = result.scalar()
    has_record = element_uuid is not None
    if not has_record:
        element_record = ImageAsset(
            user_id=None,
            name=file_path.stem,
            file_id_photo=None,
            file_id_document=None,
        )
        session.add(element_record)
        await session.commit()
        element_uuid = element_record.element_id
        logging.info("Image %s saved to db as a %s", file_path.name, element_uuid)

    try:
        _ = await store.get_info(f"0.{element_uuid}")
    except ObjectNotFoundError:
        has_content = False
    else:
        has_content = True

    if not has_content:
        await store.put(f"0.{element_uuid}", file_path.read_bytes())
        logging.info("Image %s saved to object store", file_path.name)

    if has_content and has_record:
        logging.info("Image %s already uploaded", file_path.name)


async def main(
    folder: Path,
    db_url: str,
    nats_servers: str,
):
    if not folder.is_dir():
        logging.critical("No such directory: %s", folder)
        exit(1)

    images = list(folder.glob("*.png"))
    logging.info("Found %d images", len(images))

    engine = create_async_engine(db_url)
    session_pool = async_sessionmaker(engine, expire_on_commit=False)

    nc = await nats.connect(servers=nats_servers)
    js = nc.jetstream()
    store = await js.object_store(BUCKET_NAME)

    async with session_pool() as session:
        for image in images:
            await ensure_loaded(image, store, session)


if __name__ == "__main__":
    database_url = os.getenv("DB_URL")
    nats_servers_ = os.getenv("NATS_SERVERS")
    if database_url is None:
        logging.critical("Cannot run without database url")
        exit(2)
    if nats_servers_ is None:
        logging.critical("Cannot run instance without nats url")
        exit(2)
    log_level_ = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=log_level_,
        format="{levelname:8} [{asctime}] - {message}",
        style="{",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()

    asyncio.run(
        main(
            args.folder,
            database_url,
            nats_servers_,
        )
    )
