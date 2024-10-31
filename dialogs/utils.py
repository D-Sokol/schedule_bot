import logging
from typing import Any, Awaitable, Callable

from aiogram.types import CallbackQuery, Message

from aiogram_dialog import DialogManager, Data
from aiogram_dialog.widgets.kbd import Button


logger = logging.getLogger(__file__)


def save_to_dialog_data(key: str, value: Data) -> Callable[[CallbackQuery | Message, Any, DialogManager], Awaitable]:
    async def callback(_update: CallbackQuery | Message, _widget: Any, manager: DialogManager) -> None:
        logger.debug("Saving %s = %s", key, value)
        manager.dialog_data[key] = value
    return callback


async def not_implemented_button_handler(callback: CallbackQuery, button: Button, _manager: DialogManager):
    logging.warning("Called button [%s] which is not implemented!", button.widget_id)
    await callback.answer("Функционал не реализован.")
