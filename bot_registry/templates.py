import json
import logging
from abc import ABC, abstractmethod

from database_models import User
from services.renderer.templates import Template

from .database_mixin import DatabaseRegistryMixin


logger = logging.getLogger(__file__)


class TemplateRegistryAbstract(ABC):
    @abstractmethod
    async def get_template(self, user_id: int | None) -> Template:
        raise NotImplementedError

    @abstractmethod
    async def update_template(self, user_id: int | None, template: Template) -> None:
        raise NotImplementedError


class MockTemplateRegistry(TemplateRegistryAbstract):
    async def get_template(self, user_id: int | None) -> Template:
        return Template()

    async def update_template(self, user_id: int | None, template: Template) -> None:
        pass


class DbTemplateRegistry(TemplateRegistryAbstract, DatabaseRegistryMixin):
    async def get_template(self, user_id: int | None) -> Template | None:
        if user_id is None:
            return None
        user: User | None = await self.session.get(User, user_id)
        if user is None or (template_data := user.user_template) is None:
            return None

        template_dict = json.loads(template_data)
        template = Template.model_validate(template_dict)
        return template

    async def update_template(self, user_id: int | None, template: Template) -> None:
        logger.info("Saving template for user %d", user_id)
        if user_id is None:
            logger.error("Cannot save template in global scope!")
            return
        user: User | None = await self.session.get(User, user_id)
        if user is None:
            logger.error("Cannot save schedule for unknown user id %d", user_id)
            return

        user.user_template = template.model_dump_json(exclude_defaults=False, by_alias=True)
        self.session.add(user)
        await self.session.commit()
