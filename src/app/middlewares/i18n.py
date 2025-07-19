import logging
from typing import Any, Awaitable, Callable, cast

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from fluentogram import TranslatorHub

from core.entities import UserEntity

logger = logging.getLogger(__name__)


I18N_KEY = "i18n"
TRANSLATOR_HUB_KEY = "i18n_hub"
USED_LOCALE_KEY = "i18n_locale"


class TranslatorRunnerMiddleware(BaseMiddleware):
    def __init__(self, translator_hub: TranslatorHub):
        self.hub = translator_hub

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = cast(TgUser | None, data.get("event_from_user"))
        if tg_user is None:
            return await handler(event, data)

        db_user = cast(UserEntity, data.get("user"))
        if db_user is None:
            logger.error("Wrong middleware setting: no user entity provided!")
            locale_from_db = None
        else:
            locale_from_db = db_user.preferred_language

        target_locale = locale_from_db or tg_user.language_code
        data[TRANSLATOR_HUB_KEY] = self.hub
        data[I18N_KEY] = self.hub.get_translator_by_locale(locale=target_locale)
        data[USED_LOCALE_KEY] = target_locale

        return await handler(event, data)
