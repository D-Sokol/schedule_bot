import logging
from abc import ABC, abstractmethod
from typing import final

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from bot_registry.database_models import UserModel, UserSettingsModel
from core.entities import PreferredLanguage, UserEntity

from .database_mixin import DatabaseRegistryMixin

logger = logging.getLogger(__name__)


class UserRegistryAbstract(ABC):
    @abstractmethod
    async def get_or_create_user(self, tg_id: int) -> UserEntity:
        raise NotImplementedError

    @abstractmethod
    async def get_user(self, tg_id: int) -> UserEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def grant_admin(self, tg_id: int) -> None:
        pass

    @abstractmethod
    async def revoke_admin(self, tg_id: int) -> None:
        pass

    @abstractmethod
    async def ban_user(self, tg_id: int) -> None:
        pass

    @abstractmethod
    async def unban_user(self, tg_id: int) -> None:
        pass

    @abstractmethod
    async def set_user_language(self, tg_id: int, lang: PreferredLanguage) -> None:
        raise NotImplementedError

    @abstractmethod
    async def set_user_compressed_warning(self, tg_id: int, allow_uncompressed: bool) -> None:
        raise NotImplementedError

    @classmethod
    @final
    def _convert_to_entity(cls, user_db: UserModel) -> UserEntity:
        return UserEntity(
            telegram_id=user_db.tg_id,
            is_admin=user_db.is_admin,
            is_banned=user_db.is_banned,
            accept_compressed=user_db.settings.accept_compressed if user_db.settings else False,
            preferred_language=user_db.settings.preferred_lang if user_db.settings else None,
        )


class DbUserRegistry(UserRegistryAbstract, DatabaseRegistryMixin):
    async def get_or_create_user(self, tg_id: int) -> UserEntity:
        statement = insert(UserModel).values((tg_id, False)).on_conflict_do_nothing()
        await self.session.execute(statement)
        await self.session.commit()

        user = await self.get_user(tg_id)
        assert user is not None
        return user

    async def get_user(self, tg_id: int) -> UserEntity | None:
        user: UserModel | None = await self.session.get(UserModel, tg_id)
        return self._convert_to_entity(user) if user else None

    async def grant_admin(self, tg_id: int) -> None:
        statement = (
            insert(UserModel)
            .values((tg_id, True))
            .on_conflict_do_update(index_elements=("tg_id",), set_={"is_admin": True})
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def revoke_admin(self, tg_id: int) -> None:
        # User is never created in this function because not being an admin is default thing.
        statement = update(UserModel).where(UserModel.tg_id == tg_id).values(is_admin=False)

        await self.session.execute(statement)
        await self.session.commit()

    async def ban_user(self, tg_id: int) -> None:
        statement = (
            insert(UserModel)
            .values((tg_id, False, True))
            .on_conflict_do_update(index_elements=("tg_id",), set_={"is_admin": False, "is_banned": True})
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def unban_user(self, tg_id: int) -> None:
        # User is never created in this function because not being banned is, again, default thing.
        statement = update(UserModel).where(UserModel.tg_id == tg_id).values(is_admin=False, is_banned=False)

        await self.session.execute(statement)
        await self.session.commit()

    async def _ensure_settings_obj(self, tg_id: int) -> UserSettingsModel:
        statement = insert(UserSettingsModel).values((tg_id,)).on_conflict_do_nothing()
        await self.session.execute(statement)
        settings: UserSettingsModel | None = await self.session.get(UserSettingsModel, tg_id)
        assert settings is not None, "Incorrect settings creation process!"
        return settings

    async def set_user_language(self, tg_id: int, lang: PreferredLanguage) -> None:
        settings = await self._ensure_settings_obj(tg_id)
        if settings.preferred_lang == lang:
            logger.debug("Skipping update of user %d language, already set to %s", tg_id, lang)
            return
        settings.preferred_lang = lang
        self.session.add(settings)
        await self.session.commit()

    async def set_user_compressed_warning(self, tg_id: int, allow_uncompressed: bool) -> None:
        settings = await self._ensure_settings_obj(tg_id)
        if settings.accept_compressed == allow_uncompressed:
            logger.debug("Skipping update of user %d compressed settings, already set to %s", tg_id, allow_uncompressed)
            return
        settings.accept_compressed = allow_uncompressed
        self.session.add(settings)
        await self.session.commit()
