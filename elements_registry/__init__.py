import io
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import *

from PIL import Image

logger = logging.getLogger("elements_registry")


@dataclass
class ElementRecord:
    name: str
    id: int
    file_id_photo: str | None = None
    file_id_document: str | None = None


class ElementsRegistryAbstract(ABC):
    # Elements
    @abstractmethod
    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        raise NotImplementedError

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
            file_id_photo: str | None = None,
            file_id_document: str | None = None,
            target_size: tuple[int, int] | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> None:
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

    # Templates
    @abstractmethod
    async def get_template(self, user_id: int | None) -> dict[str, Any]:
        raise NotImplementedError

    # Other
    @classmethod
    def generate_trivial_name(cls) -> str:
        now = datetime.now()
        return f"Фон {now.isoformat(sep=' ', timespec='seconds')}"


class MockElementRegistry(ElementsRegistryAbstract):
    def __init__(self):
        self.items = [
            ElementRecord(name="Фон 1", id=1),
            ElementRecord(name="Фон 2", id=2),
        ]

    # Elements
    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        return self.items

    async def get_element(self, user_id: int | None, element_id: int) -> ElementRecord:
        return self.items[element_id - 1]  # In the mock data ids are 1-based.

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
            file_id_photo: str | None = None,
            file_id_document: str | None = None,
            target_size: tuple[int, int] | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> None:
        logger.info("Saving %s (size %s) as '%s', mode=%s", element, element.size, element_name, resize_mode)
        next_id = self.items[-1].id + 1 if self.items else 0
        self.items.append(
            ElementRecord(
                name=element_name,
                id=next_id,
                file_id_photo=file_id_photo,
                file_id_document=file_id_document,
            )
        )

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

    # Templates
    async def get_template(self, user_id: int | None) -> dict[str, Any]:
        template = {"width": 1280, "height": 720}
        return template
