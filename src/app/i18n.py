import logging
from pathlib import Path

from fluent_compiler.bundle import FluentBundle
from fluentogram import TranslatorHub, FluentTranslator

logger = logging.getLogger(__name__)


_LOCALES_ROOT = Path("locales")
assert _LOCALES_ROOT.is_dir(), "localized messages directory is missing"
_MESSAGES_SUBDIR_NAME = "LC_MESSAGES"


def create_translator_hub() -> TranslatorHub:
    all_locales = all_translator_locales()
    translator_hub = TranslatorHub(
        {locale: (locale,) for locale in all_locales},
        [
            FluentTranslator(
                locale=locale,
                translator=FluentBundle.from_files(
                    locale=locale,
                    filenames=list(_LOCALES_ROOT.joinpath(locale, _MESSAGES_SUBDIR_NAME).glob("*.ftl")),
                ),
            )
            for locale in all_locales
        ],
        root_locale="ru",
    )
    return translator_hub


def all_translator_locales() -> list[str]:
    return [d.name for d in _LOCALES_ROOT.glob("*")]


def root_locale() -> str:
    root_loc = "ru"
    assert root_loc in all_translator_locales(), "No files for the root locale found!"
    return root_loc
