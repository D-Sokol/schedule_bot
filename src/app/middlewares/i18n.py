import logging
from typing import Any, Awaitable, Callable, cast

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from fluentogram import TranslatorHub

logger = logging.getLogger(__name__)


class TranslatorRunnerMiddleware(BaseMiddleware):
    def __init__(self, translator_hub: TranslatorHub):
        self.hub = translator_hub

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = cast(TgUser | None, data.get("event_from_user"))

        if user is None:
            return await handler(event, data)

        data["i18n"] = self.hub.get_translator_by_locale(locale=user.language_code)

        return await handler(event, data)
