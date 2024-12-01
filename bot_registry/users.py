from abc import ABC, abstractmethod

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


class MockUserRegistry(UserRegistryAbstract):
    async def get_or_create_user(self, tg_id: int) -> User:
        return User(tg_id=tg_id, is_admin=False)

    async def get_user(self, tg_id: int) -> User | None:
        return None


class DbUserRegistry(UserRegistryAbstract, DatabaseRegistryMixin):
    async def get_or_create_user(self, tg_id: int) -> User:
        await self.session.execute(insert(User).values((tg_id,)).on_conflict_do_nothing())
        await self.session.commit()

        user = await self.get_user(tg_id)
        assert user is not None
        return user

    async def get_user(self, tg_id: int) -> User | None:
        user: User | None = await self.session.get(User, tg_id)
        return user
