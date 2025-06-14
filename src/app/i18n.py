import logging
from pathlib import Path

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
