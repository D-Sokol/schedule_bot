from abc import ABC, abstractmethod
from typing import final

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from core.database_models import User
from core.models import UserModel

from .database_mixin import DatabaseRegistryMixin


class UserRegistryAbstract(ABC):
    @abstractmethod
    async def get_or_create_user(self, tg_id: int) -> UserModel:
        raise NotImplementedError

    @abstractmethod
    async def get_user(self, tg_id: int) -> UserModel | None:
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

    @classmethod
    @final
    def _convert_to_model(cls, user_db: User) -> UserModel:
        return UserModel(
            telegram_id=user_db.tg_id,
            is_admin=user_db.is_admin,
            is_banned=user_db.is_banned,
        )


class DbUserRegistry(UserRegistryAbstract, DatabaseRegistryMixin):
    async def get_or_create_user(self, tg_id: int) -> UserModel:
        statement = insert(User).values((tg_id, False)).on_conflict_do_nothing()
        await self.session.execute(statement)
        await self.session.commit()

        user = await self.get_user(tg_id)
        assert user is not None
        return user

    async def get_user(self, tg_id: int) -> UserModel | None:
        user: User | None = await self.session.get(User, tg_id)
        return self._convert_to_model(user) if user else None

    async def grant_admin(self, tg_id: int) -> None:
        statement = (
            insert(User).values((tg_id, True)).on_conflict_do_update(index_elements=("tg_id",), set_={"is_admin": True})
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def revoke_admin(self, tg_id: int) -> None:
        # User is never created in this function because not being an admin is default thing.
        statement = update(User).where(User.tg_id == tg_id).values(is_admin=False)

        await self.session.execute(statement)
        await self.session.commit()

    async def ban_user(self, tg_id: int) -> None:
        statement = (
            insert(User)
            .values((tg_id, False, True))
            .on_conflict_do_update(index_elements=("tg_id",), set_={"is_admin": False, "is_banned": True})
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def unban_user(self, tg_id: int) -> None:
        # User is never created in this function because not being banned is, again, default thing.
        statement = update(User).where(User.tg_id == tg_id).values(is_admin=False, is_banned=False)

        await self.session.execute(statement)
        await self.session.commit()
