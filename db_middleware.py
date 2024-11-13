from typing import Callable, ClassVar, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot_registry.users import DbUserRegistry


class DbSessionMiddleware(BaseMiddleware):
    _SESSION_KEY: ClassVar[str] = "session"

    def __init__(self, session_pool: async_sessionmaker):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            user_registry = DbUserRegistry(session)
            user = await user_registry.get_user(event.from_user.id)
            data["user_registry"] = user_registry
            data["user"] = user
            return await handler(event, data)
