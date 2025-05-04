from abc import ABC, abstractmethod

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from database_models import User

from .database_mixin import DatabaseRegistryMixin


class UserRegistryAbstract(ABC):
    @abstractmethod
    async def get_or_create_user(self, tg_id: int) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_user(self, tg_id: int) -> User | None:
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


class DbUserRegistry(UserRegistryAbstract, DatabaseRegistryMixin):
    async def get_or_create_user(self, tg_id: int) -> User:
        statement = insert(User).values((tg_id, False)).on_conflict_do_nothing()
        await self.session.execute(statement)
        await self.session.commit()

        user = await self.get_user(tg_id)
        assert user is not None
        return user

    async def get_user(self, tg_id: int) -> User | None:
        user: User | None = await self.session.get(User, tg_id)
        return user

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
