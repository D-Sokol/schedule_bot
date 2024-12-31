import logging
from abc import ABC, abstractmethod

from services.renderer.templates import Template


logger = logging.getLogger(__file__)


class TemplateRegistryAbstract(ABC):
    @abstractmethod
    async def get_template(self, user_id: int | None) -> Template:
        raise NotImplementedError


class MockTemplateRegistry(TemplateRegistryAbstract):
    async def get_template(self, user_id: int | None) -> Template:
        return Template()
