import json
import logging
from abc import ABC, abstractmethod

from bot_registry.database_models import UserModel
from core.entities import TemplateEntity

from .database_mixin import DatabaseRegistryMixin

logger = logging.getLogger(__name__)


class TemplateRegistryAbstract(ABC):
    @abstractmethod
    async def get_template(self, user_id: int | None) -> TemplateEntity:
        raise NotImplementedError

    @abstractmethod
    async def update_template(self, user_id: int | None, template: TemplateEntity | None) -> None:
        raise NotImplementedError

    async def clear_template(self, user_id: int | None) -> None:
        await self.update_template(user_id, template=None)


class DbTemplateRegistry(TemplateRegistryAbstract, DatabaseRegistryMixin):
    async def get_template(self, user_id: int | None) -> TemplateEntity | None:
        user: UserModel | None = await self.session.get(UserModel, user_id or 0)
        if user is None or (template_data := user.user_template) is None:
            return None

        template_dict = json.loads(template_data)
        template = TemplateEntity.model_validate(template_dict)
        return template

    async def update_template(self, user_id: int | None, template: TemplateEntity | None) -> None:
        logger.info("Saving template for user %d", user_id)
        user: UserModel | None = await self.session.get(UserModel, user_id or 0)
        if user is None:
            logger.error("Cannot save template for unknown user id %d", user_id)
            return

        user.user_template = template.model_dump_json(by_alias=True, exclude_none=True) if template else None
        self.session.add(user)
        await self.session.commit()
