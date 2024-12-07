from abc import ABC, abstractmethod

from sqlalchemy.dialects.postgresql import insert

from database_models import User

from .database_mixin import DatabaseRegistryMixin


class UserRegistryAbstract(ABC):
    @abstractmethod
    async def get_or_create_user(self, tg_id: int, create_admin: bool = False) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_user(self, tg_id: int) -> User | None:
        raise NotImplementedError


class MockUserRegistry(UserRegistryAbstract):
    async def get_or_create_user(self, tg_id: int, create_admin: bool = False) -> User:
        return User(tg_id=tg_id, is_admin=create_admin)

    async def get_user(self, tg_id: int) -> User | None:
        return None


class DbUserRegistry(UserRegistryAbstract, DatabaseRegistryMixin):
    async def get_or_create_user(self, tg_id: int, create_admin: bool = False) -> User:
        statement = insert(User).values((tg_id, create_admin))
        if create_admin:
            # Only called from start check, so user should become admin even if they are already registered.
            statement = statement.on_conflict_do_update(index_elements=("tg_id",), set_={"is_admin": True})
        else:
            # Middleware calls this method with default arguments, so we should not revoke admin privileges here.
            statement = statement.on_conflict_do_nothing()

        await self.session.execute(statement)
        await self.session.commit()

        user = await self.get_user(tg_id)
        assert user is not None
        return user

    async def get_user(self, tg_id: int) -> User | None:
        user: User | None = await self.session.get(User, tg_id)
        return user
