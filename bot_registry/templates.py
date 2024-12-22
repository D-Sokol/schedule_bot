import logging
from abc import ABC, abstractmethod
from typing import Any


logger = logging.getLogger(__file__)


class TemplateRegistryAbstract(ABC):
    @abstractmethod
    async def get_template(self, user_id: int | None) -> dict[str, Any]:
        raise NotImplementedError


class MockTemplateRegistry(TemplateRegistryAbstract):
    async def get_template(self, user_id: int | None) -> dict[str, Any]:
        template = {"width": 1280, "height": 720}
        return template
