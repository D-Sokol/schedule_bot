import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import *

from PIL import Image

logger = logging.getLogger("elements_registry")


@dataclass
class ElementRecord:
    name: str
    id: int
    file_id: str | None


class ElementsRegistryAbstract(ABC):
    @abstractmethod
    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        raise NotImplementedError

    @abstractmethod
    async def get_element(self, user_id: int | None, element_id: int) -> ElementRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_element_content(self, user_id: int | None, element_id: int) -> Image.Image:
        raise NotImplementedError

    @abstractmethod
    async def get_template(self, user_id: int | None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def save_element(
            self,
            element: Image.Image,
            user_id: int | None,
            element_name: str,
            file_id: str | None = None,
            target_size: tuple[int, int] | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_element_file_id(self, user_id: int | None, element_id: int, file_id: str | None):
        raise NotImplementedError


class MockElementRegistry(ElementsRegistryAbstract):
    def __init__(self):
        self.items = [
            ElementRecord(name="Фон 1", id=1, file_id=None),
            ElementRecord(name="Фон 2", id=2, file_id=None),
        ]

    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        return self.items

    async def get_element(self, user_id: int | None, element_id: int) -> ElementRecord:
        return self.items[element_id - 1]  # In the mock data ids are 1-based.

    async def get_element_content(self, user_id: int | None, element_id: int) -> Image.Image:
        return Image.new("RGBA", (200, 200), "black")

    async def get_template(self, user_id: int | None) -> dict[str, Any]:
        template = {"width": 1280, "height": 720}
        return template

    async def save_element(
            self,
            element: Image.Image,
            user_id: int | None,
            element_name: str,
            file_id: str | None = None,
            target_size: tuple[int, int] | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> None:
        logger.info("Saving %s (size %s) as '%s', mode=%s", element, element.size, element_name, resize_mode)
        self.items.append(
            ElementRecord(name=element_name, id=self.items[-1].id + 1, file_id=file_id)
        )

    async def update_element_file_id(self, user_id: int | None, element_id: int, file_id: str | None):
        logger.debug("Save file_id %s for element %s.%d", file_id, user_id, element_id)
