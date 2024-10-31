from typing import Any, Awaitable, Callable

from aiogram.types import CallbackQuery, Message

from aiogram_dialog import DialogManager, Data
from aiogram_dialog.widgets.kbd import Button


def save_to_dialog_data(key: str, value: Data) -> Callable[[CallbackQuery | Message, Any, DialogManager], Awaitable]:
    async def callback(_update: CallbackQuery | Message, _widget: Any, manager: DialogManager) -> None:
        manager.dialog_data[key] = value
    return callback


async def not_implemented_button_handler(callback: CallbackQuery, _button: Button, _manager: DialogManager):
    await callback.answer("Функционал не реализован.")
