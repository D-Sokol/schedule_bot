from typing import Callable, ClassVar, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from nats.js import JetStreamContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot_registry import DbElementRegistry, DbUserRegistry, DbTemplateRegistry, DbScheduleRegistry


class DbSessionMiddleware(BaseMiddleware):
    _SESSION_KEY: ClassVar[str] = "session"

    def __init__(self, session_pool: async_sessionmaker, js: JetStreamContext):
        super().__init__()
        self.session_pool = session_pool
        self.js = js

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            user_registry = DbUserRegistry(session)
            element_registry = DbElementRegistry(session=session, js=self.js)
            schedule_registry = DbScheduleRegistry(session=session, js=self.js, i18n=data["i18n"])
            template_registry = DbTemplateRegistry(session=session)
            data["user_registry"] = user_registry
            data["element_registry"] = element_registry
            data["schedule_registry"] = schedule_registry
            data["template_registry"] = template_registry

            if (tg_user := event.from_user) is not None:
                user = await user_registry.get_or_create_user(tg_user.id)
                data["user"] = user

            return await handler(event, data)
