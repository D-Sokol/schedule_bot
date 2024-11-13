from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database_models import User

from .database_mixin import DatabaseRegistryMixin


class UserRegistryAbstract(ABC):
    @abstractmethod
    async def get_user(self, tg_id: int) -> User:
        pass


class MockUserRegistry(UserRegistryAbstract):
    async def get_user(self, tg_id: int) -> User:
        return User(tg_id=tg_id, is_admin=False)


class DbUserRegistry(UserRegistryAbstract, DatabaseRegistryMixin):
    async def get_user(self, tg_id: int) -> User:
        await self.session.execute(insert(User).values((tg_id,)).on_conflict_do_nothing())
        await self.session.commit()
        result = await self.session.execute(select(User).where(User.tg_id == tg_id))
        user, = result.one()
        return user
