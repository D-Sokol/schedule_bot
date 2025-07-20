import logging
from enum import StrEnum
from typing import Any, cast

from aiogram import F
from aiogram.enums import MessageOriginType
from aiogram.types import Message, MessageOriginUser
from aiogram.utils.magic_filter import MagicFilter
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory

from .custom_widgets import FluentFormat, RequestUsers
from .states import UserSelectionStates

logger = logging.getLogger(__name__)

DIALOG_HELP_TYPE_KEY = "help"
DIALOG_USER_ID_KEY = "user_id"


class _HelpType(StrEnum):
    HIDDEN_USER = "hidden_user"
    UNPARSEABLE = "unparseable"


async def accept_forwarded(
    message: Message,
    _: MessageInput,
    manager: DialogManager,
) -> None:
    tg_id = cast(MessageOriginUser, message.forward_origin).sender_user.id
    await manager.done({DIALOG_USER_ID_KEY: tg_id})


async def accept_forwarded_unavailable(
    _message: Message,
    _: MessageInput,
    manager: DialogManager,
) -> None:
    manager.dialog_data[DIALOG_HELP_TYPE_KEY] = _HelpType.HIDDEN_USER


async def accept_typed_id(
    _message: Message,
    _widget: Any,
    manager: DialogManager,
    data: int,
):
    if data <= 0:
        manager.dialog_data[DIALOG_HELP_TYPE_KEY] = _HelpType.UNPARSEABLE
        return
    await manager.done({DIALOG_USER_ID_KEY: data})


async def accept_shared_contact(
    message: Message,
    _: MessageInput,
    manager: DialogManager,
):
    shared_user = message.user_shared
    assert shared_user is not None, "Incorrect filter condition"
    await manager.done({DIALOG_USER_ID_KEY: shared_user.user_id})


async def incorrect_typed_id(
    _message: Message,
    _widget: Any,
    manager: DialogManager,
    _error: ValueError,
):
    manager.dialog_data[DIALOG_HELP_TYPE_KEY] = _HelpType.UNPARSEABLE


start_window = Window(
    FluentFormat("dialog-users"),
    FluentFormat(
        "dialog-users.hidden_user",
        when=cast(MagicFilter, F["dialog_data"][DIALOG_HELP_TYPE_KEY] == _HelpType.HIDDEN_USER),
    ),
    FluentFormat(
        "dialog-users.unparseable_text",
        when=cast(MagicFilter, F["dialog_data"][DIALOG_HELP_TYPE_KEY] == _HelpType.UNPARSEABLE),
    ),
    RequestUsers(FluentFormat("dialog-users.share"), max_quantity=1, request_photo=True, request_username=False),
    Cancel(FluentFormat("dialog-cancel")),
    MessageInput(func=accept_forwarded, filter=cast(MagicFilter, F.forward_origin.type == MessageOriginType.USER)),
    MessageInput(func=accept_forwarded_unavailable, filter=cast(MagicFilter, F.forward_origin)),
    MessageInput(func=accept_shared_contact, filter=cast(MagicFilter, F.user_shared)),
    TextInput(id="id_input", type_factory=int, on_success=accept_typed_id, on_error=incorrect_typed_id),
    state=UserSelectionStates.START,
    markup_factory=ReplyKeyboardFactory(resize_keyboard=True, one_time_keyboard=True),
)


dialog = Dialog(
    start_window,
    name=__name__,
)
