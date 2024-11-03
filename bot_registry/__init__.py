import logging
from abc import ABC

from .image_assets import ElementRecord, ElementsRegistryAbstract, MockElementRegistry
from .templates import TemplateRegistryAbstract, MockTemplateRegistry
from .texts import Schedule, ScheduleRegistryAbstract, MockScheduleRegistry

logger = logging.getLogger(__file__)


class RegistryAbstract(ElementsRegistryAbstract, TemplateRegistryAbstract, ScheduleRegistryAbstract, ABC):
    pass


class MockRegistry(RegistryAbstract, MockElementRegistry, MockTemplateRegistry, MockScheduleRegistry):
    pass
