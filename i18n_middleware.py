import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from fluent_compiler.bundle import FluentBundle
from fluentogram import TranslatorHub, FluentTranslator

logger = logging.getLogger(__name__)


def create_translator_hub() -> TranslatorHub:
    translator_hub = TranslatorHub(
        {
            "ru": ("ru",),
        },
        [
            FluentTranslator(
                locale="ru",
                translator=FluentBundle.from_files(
                    locale="ru-RU",
                    filenames=[
                        "locales/ru/LC_MESSAGES/dialogs.ftl",
                        "locales/ru/LC_MESSAGES/notifications.ftl",
                    ],
                )
            ),
        ],
        root_locale="ru",
    )
    return translator_hub


class TranslatorRunnerMiddleware(BaseMiddleware):
    def __init__(self, translator_hub: TranslatorHub):
        self.hub = translator_hub

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:

        user: User = data.get('event_from_user')

        if user is None:
            return await handler(event, data)

        data['i18n'] = self.hub.get_translator_by_locale(locale=user.language_code)

        return await handler(event, data)
