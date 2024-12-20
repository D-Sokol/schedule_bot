import io
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import *
from uuid import UUID

from PIL import Image
from sqlalchemy import func, select, update, delete

from database_models import ImageAsset

from .database_mixin import DatabaseRegistryMixin

logger = logging.getLogger(__file__)


LOCAL_SCOPE_ELEMENTS_LIMIT = 6
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


class MockElementRegistry(ElementsRegistryAbstract):
    def __init__(self):
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


class DbElementRegistry(ElementsRegistryAbstract, DatabaseRegistryMixin):
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
        return result.scalar()

    async def get_elements_count(self, user_id: int | None) -> int:
        result = await self.session.execute(
            select(func.count(ImageAsset.element_id)).where(ImageAsset.user_id == user_id)
        )
        return result.scalar()

    async def get_element_content(self, user_id: int | None, element_id: str | UUID) -> bytes:
        raise NotImplementedError

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
        _ = element
        element_record = ImageAsset(
            user_id=user_id,
            name=element_name,
            file_id_photo=file_id_photo,
            file_id_document=file_id_document,
        )
        self.session.add(element_record)
        await self.session.commit()
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
