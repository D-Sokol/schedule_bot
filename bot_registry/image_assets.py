import io
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import ClassVar, Literal, cast, final
from uuid import UUID

import sqlalchemy.exc
from PIL import Image
from nats.js.errors import ObjectNotFoundError
from nats.js.object_store import ObjectStore
from sqlalchemy import func, select, update, delete

from services.converter import IMAGE_FORMAT, SAVE_NAME_HEADER, RESIZE_MODE_HEADER, TARGET_SIZE_HEADER
from database_models import ImageAsset
from exceptions import ImageNotProcessedException, DuplicateNameException, ImageContentEmpty, ImageNotExist

from .database_mixin import DatabaseRegistryMixin
from .nats_mixin import NATSRegistryMixin

logger = logging.getLogger(__file__)


LOCAL_SCOPE_ELEMENTS_LIMIT = 10
GLOBAL_SCOPE_ELEMENTS_LIMIT = 1_000


class ElementsRegistryAbstract(ABC):
    @abstractmethod
    async def get_elements(self, user_id: int | None) -> list[ImageAsset]:
        raise NotImplementedError

    async def get_elements_count(self, user_id: int | None) -> int:
        items = await self.get_elements(user_id)
        return len(items)

    @abstractmethod
    async def get_element(self, user_id: int | None, element_id: str | UUID) -> ImageAsset:
        raise NotImplementedError

    async def is_element_content_ready(self, user_id: int | None, element_id: str | UUID) -> bool:
        try:
            _ = self.get_element_content(user_id, element_id)
        except ImageNotProcessedException:
            return False
        else:
            return True

    @abstractmethod
    async def get_element_content(self, user_id: int | None, element_id: str | UUID) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def save_element(
            self,
            element: Image.Image,
            user_id: int | None,
            element_name: str,
            target_size: tuple[int, int],
            file_id_photo: str | None = None,
            file_id_document: str | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> ImageAsset:
        raise NotImplementedError

    @abstractmethod
    async def update_element_file_id(
            self,
            user_id: int | None,
            element_id: str | UUID,
            file_id: str | None,
            file_type: Literal["photo", "document"] = "document",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_element_name(self, user_id: int | None, element_id: str | UUID, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reorder_make_first(self, user_id: int | None, element_id: str | UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reorder_make_last(self, user_id: int | None, element_id: str | UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_element(self, user_id: int | None, element_id: str | UUID) -> None:
        raise NotImplementedError

    @classmethod
    async def get_elements_limit(cls, user_id: int | None) -> int:
        return GLOBAL_SCOPE_ELEMENTS_LIMIT if user_id is None else LOCAL_SCOPE_ELEMENTS_LIMIT

    @classmethod
    def generate_trivial_name(cls) -> str:
        now = datetime.now()
        return f"Фон {now.isoformat(sep=' ', timespec='seconds')}"

    @classmethod
    @final
    def validate_name(cls, name: str) -> str:
        if len(name) > 50:
            raise ValueError(f"Name is too long: {len(name)}")
        return name

    BOT_URI_PREFIX = "bot://"

    @classmethod
    @final
    def format_bot_uri(cls, user_id: int | None, element_id: str | UUID) -> str:
        return f"{cls.BOT_URI_PREFIX}{user_id or 0}/{element_id}"

    @classmethod
    @final
    def parse_bot_uri(cls, bot_uri: str) -> tuple[int | None, str]:
        if not bot_uri.startswith(cls.BOT_URI_PREFIX):
            raise ValueError(f"Not a bot URI: {bot_uri}")
        bot_uri = bot_uri.removeprefix(cls.BOT_URI_PREFIX)
        user_id, element_id = bot_uri.split("/")
        return int(user_id) or None, element_id

class MockElementRegistry(ElementsRegistryAbstract):
    def __init__(self) -> None:
        self.default_items = [
            ImageAsset(name="Фон 1", element_id="1"),
            ImageAsset(name="Фон 2", element_id="2"),
        ]
        self.items: dict[int | None, list] = defaultdict(lambda: self.default_items.copy())

    async def get_elements(self, user_id: int | None) -> list[ImageAsset]:
        return self.items[user_id]

    async def get_element(self, user_id: int | None, element_id: str | UUID) -> ImageAsset:
        return self.items[user_id][int(element_id) - 1]  # In the mock data ids are 1-based.

    async def get_element_content(self, user_id: int | None, element_id: str | UUID) -> bytes:
        image = Image.new("RGBA", (200, 200), "black")
        stream = io.BytesIO()
        image.save(stream, format="png")
        return stream.getvalue()

    async def save_element(
            self,
            element: Image.Image,
            user_id: int | None,
            element_name: str,
            target_size: tuple[int, int],
            file_id_photo: str | None = None,
            file_id_document: str | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> ImageAsset:
        logger.info("Saving %s (size %s) as '%s', mode=%s", element, element.size, element_name, resize_mode)
        next_id = int(self.items[user_id][-1].element_id) + 1 if self.items[user_id] else 0
        new_record = ImageAsset(
            name=element_name,
            id=next_id,
            file_id_photo=file_id_photo,
            file_id_document=file_id_document,
        )
        self.items[user_id].append(new_record)
        return new_record

    async def update_element_file_id(
            self,
            user_id: int | None,
            element_id: str | UUID,
            file_id: str | None,
            file_type: Literal["photo", "document"] = "document",
    ) -> None:
        logger.debug("Save file_id %s for element %s.%d/%s", file_id, user_id, element_id, file_type)
        item = await self.get_element(user_id, element_id)
        if file_type == "photo":
            item.file_id_photo = file_id
        elif file_type == "document":
            item.file_id_document = file_id
        else:
            logger.error("Trying to update file_id for unknown file_type: %s", file_type)

    async def update_element_name(self, user_id: int | None, element_id: str | UUID, name: str) -> None:
        pass

    async def reorder_make_first(self, user_id: int | None, element_id: str | UUID) -> None:
        pass

    async def reorder_make_last(self, user_id: int | None, element_id: str | UUID) -> None:
        pass

    async def delete_element(self, user_id: int | None, element_id: str | UUID) -> None:
        pass


class DbElementRegistry(ElementsRegistryAbstract, DatabaseRegistryMixin, NATSRegistryMixin):
    BUCKET_NAME: ClassVar[str] = "assets"
    CONVERT_SUBJECT_NAME: ClassVar[str] = "assets.convert"

    async def get_elements(self, user_id: int | None) -> list[ImageAsset]:
        result = await self.session.execute(
            select(ImageAsset).where(ImageAsset.user_id == user_id).order_by(ImageAsset.display_order.asc())
        )
        elements = result.fetchall()
        return [e for (e,) in elements]

    async def get_element(self, user_id: int | None, element_id: str | UUID) -> ImageAsset:
        result = await self.session.execute(select(ImageAsset).where(
            ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
        )
        asset = result.scalar()
        if asset is None:
            raise ImageNotExist(user_id, element_id)
        return asset

    async def get_elements_count(self, user_id: int | None) -> int:
        result = await self.session.execute(
            select(func.count(ImageAsset.element_id)).where(ImageAsset.user_id == user_id)
        )
        return cast(int, result.scalar())

    async def get_element_content(self, user_id: int | None, element_id: str | UUID) -> bytes:
        bucket = await self._bucket()
        try:
            result = await bucket.get(self._nats_object_name(user_id, element_id))
        except ObjectNotFoundError as e:
            raise ImageNotProcessedException(user_id, element_id) from e

        if not result.data:
            raise ImageContentEmpty(user_id, element_id)
        return result.data

    async def is_element_content_ready(self, user_id: int | None, element_id: str | UUID) -> bool:
        bucket = await self._bucket()
        try:
            _ = await bucket.get_info(self._nats_object_name(user_id, element_id))
        except ObjectNotFoundError:
            return False
        else:
            return True


    async def save_element(
            self,
            element: Image.Image,
            user_id: int | None,
            element_name: str,
            target_size: tuple[int, int],
            file_id_photo: str | None = None,
            file_id_document: str | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> ImageAsset:
        if resize_mode != "ignore":
            # Image will be converted somehow, therefore these file_ids for the original file is not correct.
            logging.debug("Ignore file ids because of resize mode is %s", resize_mode)
            file_id_photo = file_id_document = None

        try:
            element_record = ImageAsset(
                user_id=user_id,
                name=element_name,
                file_id_photo=file_id_photo,
                file_id_document=file_id_document,
            )
            self.session.add(element_record)
            await self.session.commit()  # sqlalchemy.exc.IntegrityError
        except sqlalchemy.exc.IntegrityError as e:
            raise DuplicateNameException(element_name) from e

        stream = io.BytesIO()
        element.save(stream, format=IMAGE_FORMAT)
        await self.js.publish(
            subject=self.CONVERT_SUBJECT_NAME,
            payload=stream.getvalue(),
            headers={
                SAVE_NAME_HEADER: self._nats_object_name(user_id, element_record.element_id),
                RESIZE_MODE_HEADER: resize_mode,
                TARGET_SIZE_HEADER: json.dumps(target_size)
            },
        )
        return element_record

    async def update_element_file_id(
            self,
            user_id: int | None,
            element_id: str | UUID,
            file_id: str | None,
            file_type: Literal["photo", "document"] = "document",
    ) -> None:
        update_field = f"file_id_{file_type}"
        await self.session.execute(
            update(ImageAsset)
            .where(ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
            .values(**{update_field: file_id})
        )
        await self.session.commit()

    async def update_element_name(self, user_id: int | None, element_id: str | UUID, name: str) -> None:
        logger.info("Renaming %s/%s to %s", user_id, element_id, name)
        await self.session.execute(
            update(ImageAsset)
            .where(ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
            .values(name=name)
        )
        await self.session.commit()

    async def reorder_make_first(self, user_id: int | None, element_id: str | UUID) -> None:
        element = await self.get_element(user_id, element_id)
        if element is None:
            logging.error("No image to update: user_id %s, element_id %s", user_id, element_id)
            return

        prev_order = element.display_order
        if prev_order <= 0:
            logger.info("Ignore reordering: %s/%s already first", user_id, element_id)
            return

        logger.info("Reorder %s/%s to first", user_id, element_id)
        await self.session.execute(
            update(ImageAsset)
            .where(ImageAsset.user_id == user_id, ImageAsset.display_order < prev_order)
            .values(display_order=ImageAsset.display_order + 1)
        )

        element.display_order = 0
        self.session.add(element)

        await self.session.commit()

    async def reorder_make_last(self, user_id: int | None, element_id: str | UUID) -> None:
        element = await self.get_element(user_id, element_id)
        if element is None:
            logging.error("No image to update: user_id %s, element_id %s", user_id, element_id)
            return

        max_display_order = await self.get_elements_count(user_id) - 1
        prev_order = element.display_order
        if prev_order >= max_display_order:
            logger.info("Ignore reordering: %s/%s already last", user_id, element_id)
            return

        logger.info("Reorder %s/%s to first", user_id, element_id)
        await self.session.execute(
            update(ImageAsset)
            .where(ImageAsset.user_id == user_id, ImageAsset.display_order > prev_order)
            .values(display_order=ImageAsset.display_order - 1)
        )

        element.display_order = max_display_order
        self.session.add(element)

        await self.session.commit()

    async def delete_element(self, user_id: int | None, element_id: str | UUID) -> None:
        logger.info("Removing %s/%s", user_id, element_id)
        await self.session.execute(
            delete(ImageAsset)
            .where(ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
        )
        await self.session.commit()

    async def _bucket(self) -> ObjectStore:
        return await self.js.object_store(self.BUCKET_NAME)

    @staticmethod
    def _nats_object_name(user_id: int | None, element_id: str | UUID) -> str:
        return f"{user_id or 0}.{element_id}"
