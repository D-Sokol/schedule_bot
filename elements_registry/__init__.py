import logging
from abc import ABC, abstractmethod
from typing import *

from PIL import Image

logger = logging.getLogger("elements_registry")


class ElementRecord(TypedDict):
    name: str
    id: int
    file_id: str | None


class ElementsRegistryAbstract(ABC):
    @abstractmethod
    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
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
            target_size: tuple[int, int] | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_element_file_id(self, user_id: int | None, element_id: int, file_id: str | None):
        raise NotImplementedError


class MockElementRegistry(ElementsRegistryAbstract):
    async def get_elements(self, user_id: int | None) -> list[ElementRecord]:
        items = [
            {"name": "Фон 1", "id": 1, "file_id": None},
            {"name": "Фон 2", "id": 2, "file_id": None},
            {
                "name": "Фон с названием, созданным автоматически, без ручного ввода, от двадцать девятого октября две тысячи четвертого года нашей эры",
                "id": 3,
                "file_id": None
            },
            {"name": "Фон 4", "id": 4, "file_id": None},
            {"name": "Фон 4", "id": 5, "file_id": None},
            # {"name": "Фон 6", "id": 6, "file_id": None},
        ]
        return items

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
            target_size: tuple[int, int] | None = None,
            resize_mode: Literal["resize", "crop", "ignore"] = "ignore",
    ) -> None:
        logger.info("Saving %s (size %s) as '%s', mode=%s", element, element.size, element_name, resize_mode)


    async def update_element_file_id(self, user_id: int | None, element_id: int, file_id: str | None):
        logger.debug("Save file_id %s for element %s.%d", file_id, user_id, element_id)
