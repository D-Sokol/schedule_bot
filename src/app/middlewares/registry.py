from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, ErrorEvent
from nats.js import JetStreamContext

from app.middlewares.db_session import SESSION_KEY
from app.middlewares.i18n import I18N_KEY
from bot_registry import DbElementRegistry, DbTemplateRegistry, DbScheduleRegistry


ELEMENT_REGISTRY_KEY = "element_registry"
SCHEDULE_REGISTRY_KEY = "schedule_registry"
TEMPLATE_REGISTRY_KEY = "template_registry"


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
        session = data.get(SESSION_KEY)
        if session is None:
            raise RuntimeError("Session not found in data, ensure DbSessionMiddleware is applied first.")

        i18n = data.get(I18N_KEY)
        if i18n is None:
            raise RuntimeError("i18n not found in data, ensure TranslatorRunnerMiddleware is applied first.")

        element_registry = DbElementRegistry(session=session, js=self.js)
        schedule_registry = DbScheduleRegistry(session=session, js=self.js, i18n=i18n)
        template_registry = DbTemplateRegistry(session=session)

        data[ELEMENT_REGISTRY_KEY] = element_registry
        data[SCHEDULE_REGISTRY_KEY] = schedule_registry
        data[TEMPLATE_REGISTRY_KEY] = template_registry

        return await handler(event, data)
