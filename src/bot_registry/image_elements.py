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
from bot_registry.database_models import ImageElementModel
from core.entities import ImageEntity
from core.exceptions import ImageNotProcessedException, DuplicateNameException, ImageContentEmpty, ImageNotExist

from .database_mixin import DatabaseRegistryMixin
from .nats_mixin import NATSRegistryMixin

logger = logging.getLogger(__name__)


LOCAL_SCOPE_ELEMENTS_LIMIT = 10
GLOBAL_SCOPE_ELEMENTS_LIMIT = 1_000


class ElementsRegistryAbstract(ABC):
    @abstractmethod
    async def get_elements(self, user_id: int | None) -> list[ImageEntity]:
        raise NotImplementedError

    async def get_elements_count(self, user_id: int | None) -> int:
        items = await self.get_elements(user_id)
        return len(items)

    @abstractmethod
    async def get_element(self, user_id: int | None, element_id: str | UUID) -> ImageEntity:
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
    ) -> ImageEntity:
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
    def _convert_to_entity(cls, element_db: ImageElementModel) -> ImageEntity:
        return ImageEntity(
            element_id=element_db.element_id,
            name=element_db.name,
            file_id_photo=element_db.file_id_photo,
            file_id_document=element_db.file_id_document,
        )

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

    async def get_elements(self, user_id: int | None) -> list[ImageEntity]:
        result = await self.session.execute(
            select(ImageElementModel)
            .where(ImageElementModel.user_id == user_id)
            .order_by(ImageElementModel.display_order.asc())
        )
        elements = result.fetchall()
        return [self._convert_to_entity(e) for (e,) in elements]

    async def get_element(self, user_id: int | None, element_id: str | UUID) -> ImageEntity:
        result = await self.session.execute(
            select(ImageElementModel).where(
                ImageElementModel.user_id == user_id, ImageElementModel.element_id == element_id
            )
        )
        element = result.scalar()
        if element is None:
            raise ImageNotExist(user_id, element_id)
        return self._convert_to_entity(element)

    async def get_elements_count(self, user_id: int | None) -> int:
        result = await self.session.execute(
            select(func.count(ImageElementModel.element_id)).where(ImageElementModel.user_id == user_id)
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
    ) -> ImageEntity:
        if element is None and file_id_photo is None and file_id_document is None:
            raise ValueError("Cannot save element without image or file_id to get it")

        try:
            element_record = ImageElementModel(
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
        return self._convert_to_entity(element_record)

    async def update_element_file_id(
        self,
        user_id: int | None,
        element_id: str | UUID,
        file_id: str | None,
        file_type: Literal["photo", "document"] = "document",
    ) -> None:
        update_field = f"file_id_{file_type}"
        await self.session.execute(
            update(ImageElementModel)
            .where(ImageElementModel.user_id == user_id, ImageElementModel.element_id == element_id)
            .values(**{update_field: file_id})
        )
        await self.session.commit()

    async def update_element_name(self, user_id: int | None, element_id: str | UUID, name: str) -> None:
        logger.info("Renaming %s/%s to %s", user_id, element_id, name)
        await self.session.execute(
            update(ImageElementModel)
            .where(ImageElementModel.user_id == user_id, ImageElementModel.element_id == element_id)
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
            update(ImageElementModel)
            .where(ImageElementModel.user_id == user_id, ImageElementModel.display_order < prev_order)
            .values(display_order=ImageElementModel.display_order + 1)
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
            update(ImageElementModel)
            .where(ImageElementModel.user_id == user_id, ImageElementModel.display_order > prev_order)
            .values(display_order=ImageElementModel.display_order - 1)
        )

        element.display_order = max_display_order
        self.session.add(element)

        await self.session.commit()

    async def delete_element(self, user_id: int | None, element_id: str | UUID) -> None:
        logger.info("Removing %s/%s", user_id, element_id)
        await self.session.execute(
            update(ImageElementModel)
            .where(
                ImageElementModel.user_id == user_id,
                ImageElementModel.display_order
                > (
                    select(ImageElementModel.display_order)
                    .where(ImageElementModel.user_id == user_id, ImageElementModel.element_id == element_id)
                    .scalar_subquery()
                ),
            )
            .values(display_order=ImageElementModel.display_order - text("1"))
        )
        await self.session.execute(
            delete(ImageElementModel).where(
                ImageElementModel.user_id == user_id, ImageElementModel.element_id == element_id
            )
        )
        await self.session.commit()

    async def _bucket(self) -> ObjectStore:
        return await self.js.object_store(self.BUCKET_NAME)

    @staticmethod
    def _nats_object_name(user_id: int | None, element_id: str | UUID) -> str:
        return f"{user_id or 0}.{element_id}"
