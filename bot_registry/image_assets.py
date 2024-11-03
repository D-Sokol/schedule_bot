import io
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import *

from PIL import Image

logger = logging.getLogger(__file__)


@dataclass
class ElementRecord:
    name: str
    id: int
    file_id_photo: str | None = None
    file_id_document: str | None = None


class ElementsRegistryAbstract(ABC):
    @abstractmethod
    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        raise NotImplementedError

    async def get_elements_count(self, user_id: int | None):
        items = await self.get_elements(user_id)
        return len(items)

    @abstractmethod
    async def get_element(self, user_id: int | None, element_id: int) -> ElementRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_element_content(self, user_id: int | None, element_id: int) -> bytes:
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
    ) -> ElementRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_element_file_id(
            self,
            user_id: int | None,
            element_id: int,
            file_id: str | None,
            file_type: Literal["photo", "document"] = "document",
    ):
        raise NotImplementedError

    @classmethod
    def generate_trivial_name(cls) -> str:
        now = datetime.now()
        return f"Фон {now.isoformat(sep=' ', timespec='seconds')}"


class MockElementRegistry(ElementsRegistryAbstract):
    def __init__(self):
        self.default_items = [
            ElementRecord(name="Фон 1", id=1),
            ElementRecord(name="Фон 2", id=2),
        ]
        self.items: dict[int | None, list] = defaultdict(lambda: self.default_items.copy())

    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        return self.items[user_id]

    async def get_element(self, user_id: int | None, element_id: int) -> ElementRecord:
        return self.items[user_id][element_id - 1]  # In the mock data ids are 1-based.

    async def get_element_content(self, user_id: int | None, element_id: int) -> bytes:
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
    ) -> ElementRecord:
        logger.info("Saving %s (size %s) as '%s', mode=%s", element, element.size, element_name, resize_mode)
        next_id = self.items[user_id][-1].id + 1 if self.items[user_id] else 0
        new_record = ElementRecord(
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
            element_id: int,
            file_id: str | None,
            file_type: Literal["photo", "document"] = "document",
    ):
        logger.debug("Save file_id %s for element %s.%d/%s", file_id, user_id, element_id, file_type)
        item = await self.get_element(user_id, element_id)
        if file_type == "photo":
            item.file_id_photo = file_id
        elif file_type == "document":
            item.file_id_document = file_id
        else:
            logger.error("Trying to update file_id for unknown file_type: %s", file_type)
