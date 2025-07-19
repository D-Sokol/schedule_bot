from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, ErrorEvent
from nats.js import JetStreamContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot_registry import DbElementRegistry, DbUserRegistry, DbTemplateRegistry, DbScheduleRegistry


_SESSION_KEY = "session"
USER_REGISTRY_KEY = "user_registry"
USER_ENTITY_KEY = "user"
ELEMENT_REGISTRY_KEY = "element_registry"
SCHEDULE_REGISTRY_KEY = "schedule_registry"
TEMPLATE_REGISTRY_KEY = "template_registry"


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
            data[_SESSION_KEY] = session
            user_registry = DbUserRegistry(session)
            data[USER_REGISTRY_KEY] = user_registry

            tg_event: Message | CallbackQuery = (
                event if isinstance(event, (Message, CallbackQuery)) else event.update.event
            )

            if (tg_user := tg_event.from_user) is not None:
                user = await user_registry.get_or_create_user(tg_user.id)
                data[USER_ENTITY_KEY] = user

            return await handler(event, data)


class RegistryMiddleware(BaseMiddleware):
    def __init__(self, js: JetStreamContext):
        super().__init__()
        self.js = js

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery | ErrorEvent,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get(_SESSION_KEY)
        if session is None:
            raise RuntimeError("Session not found in data, ensure DbSessionMiddleware is applied first.")

        i18n = data.get("i18n")
        if i18n is None:
            raise RuntimeError("i18n not found in data, ensure TranslatorRunnerMiddleware is applied first.")

        element_registry = DbElementRegistry(session=session, js=self.js)
        schedule_registry = DbScheduleRegistry(session=session, js=self.js, i18n=i18n)
        template_registry = DbTemplateRegistry(session=session)

        data[ELEMENT_REGISTRY_KEY] = element_registry
        data[SCHEDULE_REGISTRY_KEY] = schedule_registry
        data[TEMPLATE_REGISTRY_KEY] = template_registry

        return await handler(event, data)
