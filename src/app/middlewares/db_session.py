from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, ErrorEvent
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot_registry import DbUserRegistry


SESSION_KEY = "session"
USER_REGISTRY_KEY = "user_registry"
USER_ENTITY_KEY = "user"


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery | ErrorEvent,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data[SESSION_KEY] = session
            user_registry = DbUserRegistry(session)
            data[USER_REGISTRY_KEY] = user_registry

            tg_event: Message | CallbackQuery = (
                event if isinstance(event, (Message, CallbackQuery)) else event.update.event
            )

            if (tg_user := tg_event.from_user) is not None:
                user = await user_registry.get_or_create_user(tg_user.id)
                data[USER_ENTITY_KEY] = user

            return await handler(event, data)
