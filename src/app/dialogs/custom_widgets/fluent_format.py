from typing import ClassVar

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text
from fluentogram import TranslatorRunner
from magic_filter import MagicFilter

from core.fluentogram_utils import clear_fluentogram_message


class FluentFormat(Text):
    MIDDLEWARE_KEY: ClassVar[str] = "i18n"

    def __init__(
        self,
        key: str,
        when: WhenCondition = None,
        **kwargs: MagicFilter | str | int,
    ):
        super().__init__(when)
        self.key = key
        self.kwargs = kwargs

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        i18n: TranslatorRunner = manager.middleware_data[self.MIDDLEWARE_KEY]
        for key, value in self.kwargs.items():
            if isinstance(value, MagicFilter):
                data[key] = value.resolve(data)
            else:
                data[key] = value

        text_value: str | None = i18n.get(self.key, **data)
        if text_value is None:
            raise ValueError(f"Missing key {self.key}")
        return clear_fluentogram_message(text_value)
