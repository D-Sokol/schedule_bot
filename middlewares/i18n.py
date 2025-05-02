import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
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
                locale=locale,
                translator=FluentBundle.from_files(
                    locale=locale,
                    filenames=list(Path(f"locales/{locale}/LC_MESSAGES/").glob("*.ftl")),
                ),
            )
            for locale in all_translator_locales()
        ],
        root_locale="ru",
    )
    return translator_hub


def all_translator_locales() -> list[str]:
    return ["ru"]


def root_locale() -> str:
    return all_translator_locales()[0]


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
