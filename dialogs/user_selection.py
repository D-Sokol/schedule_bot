import logging
from typing import cast, Any

from aiogram import F
from aiogram.types import Message, MessageOriginUser
from aiogram.utils.magic_filter import MagicFilter
from aiogram.enums import MessageOriginType
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Cancel
from .states import UserSelectionStates
from .utils import FluentFormat


logger = logging.getLogger(__file__)


async def accept_forwarded(
        message: Message,
        _: MessageInput,
        manager: DialogManager,
) -> None:
    tg_id = cast(MessageOriginUser, message.forward_origin).sender_user.id
    await manager.done({"user_id": tg_id})


async def accept_forwarded_unavailable(
        _message: Message,
        _: MessageInput,
        manager: DialogManager,
) -> None:
    manager.dialog_data["help"] = "hidden_user"


async def accept_typed_id(
        _message: Message,
        _widget: Any,
        manager: DialogManager,
        data: int,
):
    if data <= 0:
        manager.dialog_data["help"] = "unparseable"
        return
    await manager.done({"user_id": data})


async def incorrect_typed_id(
        _message: Message,
        _widget: Any,
        manager: DialogManager,
        _error: ValueError,
):
    manager.dialog_data["help"] = "unparseable"


start_window = Window(
    FluentFormat("dialog-users"),
    FluentFormat("dialog-users.hidden_user", when=cast(MagicFilter, F["dialog_data"]["help"] == "hidden_user")),
    FluentFormat("dialog-users.unparseable_text", when=cast(MagicFilter, F["dialog_data"]["help"] == "unparseable")),
    Cancel(FluentFormat("dialog-cancel")),
    MessageInput(func=accept_forwarded, filter=cast(MagicFilter, F.forward_origin.type == MessageOriginType.USER)),
    MessageInput(func=accept_forwarded_unavailable, filter=cast(MagicFilter, F.forward_origin)),
    TextInput(id="id_input", type_factory=int, on_success=accept_typed_id, on_error=incorrect_typed_id),
    state=UserSelectionStates.START,
)


dialog = Dialog(
    start_window,
    name=__file__,
)
