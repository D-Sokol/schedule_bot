import io
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar, Literal, cast, final
from uuid import UUID

import sqlalchemy.exc
from PIL import Image
from nats.js.errors import ObjectNotFoundError
from nats.js.object_store import ObjectStore
from sqlalchemy import func, select, update, delete, text

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
        element: Image.Image | None,
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


class DbElementRegistry(ElementsRegistryAbstract, DatabaseRegistryMixin, NATSRegistryMixin):
    BUCKET_NAME: ClassVar[str] = "assets"
    CONVERT_RAW_SUBJECT_NAME: ClassVar[str] = "assets.convert.raw"
    CONVERT_FILE_ID_SUBJECT_NAME: ClassVar[str] = "assets.convert.file_id"

    async def get_elements(self, user_id: int | None) -> list[ImageAsset]:
        result = await self.session.execute(
            select(ImageAsset).where(ImageAsset.user_id == user_id).order_by(ImageAsset.display_order.asc())
        )
        elements = result.fetchall()
        return [e for (e,) in elements]

    async def get_element(self, user_id: int | None, element_id: str | UUID) -> ImageAsset:
        result = await self.session.execute(
            select(ImageAsset).where(ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
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
        element: Image.Image | None,
        user_id: int | None,
        element_name: str,
        target_size: tuple[int, int],
        file_id_photo: str | None = None,
        file_id_document: str | None = None,
        resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> ImageAsset:
        if element is None and file_id_photo is None and file_id_document is None:
            raise ValueError("Cannot save element without image or file_id to get it")

        try:
            element_record = ImageAsset(
                user_id=user_id,
                name=element_name,
                file_id_photo=file_id_photo if resize_mode == "ignore" else None,
                file_id_document=file_id_document if resize_mode == "ignore" else None,
            )
            self.session.add(element_record)
            await self.session.commit()  # sqlalchemy.exc.IntegrityError
        except sqlalchemy.exc.IntegrityError as e:
            raise DuplicateNameException(element_name) from e

        if element is not None:
            stream = io.BytesIO()
            element.save(stream, format=IMAGE_FORMAT)
            payload = stream.getvalue()
            subject = self.CONVERT_RAW_SUBJECT_NAME
        else:
            file_id = file_id_document or file_id_photo
            assert file_id is not None
            payload = file_id.encode()
            subject = self.CONVERT_FILE_ID_SUBJECT_NAME

        await self.js.publish(
            subject=subject,
            payload=payload,
            headers={
                SAVE_NAME_HEADER: self._nats_object_name(user_id, element_record.element_id),
                RESIZE_MODE_HEADER: resize_mode,
                TARGET_SIZE_HEADER: json.dumps(target_size),
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
            update(ImageAsset)
            .where(
                ImageAsset.user_id == user_id,
                ImageAsset.display_order
                > (
                    select(ImageAsset.display_order)
                    .where(ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
                    .scalar_subquery()
                ),
            )
            .values(display_order=ImageAsset.display_order - text("1"))
        )
        await self.session.execute(
            delete(ImageAsset).where(ImageAsset.user_id == user_id, ImageAsset.element_id == element_id)
        )
        await self.session.commit()

    async def _bucket(self) -> ObjectStore:
        return await self.js.object_store(self.BUCKET_NAME)

    @staticmethod
    def _nats_object_name(user_id: int | None, element_id: str | UUID) -> str:
        return f"{user_id or 0}.{element_id}"
