import logging
from abc import ABC

from .image_assets import ElementRecord, ElementsRegistryAbstract, MockElementRegistry
from .templates import TemplateRegistryAbstract, MockTemplateRegistry

logger = logging.getLogger(__file__)


class RegistryAbstract(ElementsRegistryAbstract, TemplateRegistryAbstract, ABC):
    pass


class MockRegistry(RegistryAbstract, MockElementRegistry, MockTemplateRegistry):
    pass
