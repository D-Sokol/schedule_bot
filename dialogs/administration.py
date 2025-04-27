import logging
from enum import StrEnum
from functools import partial
from typing import Any

from aiogram.types import CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row
from fluentogram import TranslatorRunner

from bot_registry import UserRegistryAbstract
from .states import AdministrationStates, UserSelectionStates
from .utils import FluentFormat, current_user_id, has_admin_privileges


logger = logging.getLogger(__file__)


class ActionWithUser(StrEnum):
    GRANT_ADMIN = "grant_admin"
    REVOKE_ADMIN = "revoke_admin"
    BAN_USER = "ban_user"
    UNBAN_USER = "unban_user"


async def process_action(action: ActionWithUser, user_tg_id: int, user_registry: UserRegistryAbstract):
    logger.error("Cannot perform action %s", action)  # TODO. Also check privileges


async def on_dialog_start(start_data: dict[str, Any] | None, manager: DialogManager):
    if start_data is None:
        return

    user_id: int | None = start_data.get("user_id")
    action: ActionWithUser | None = start_data.get("action")
    if user_id is None is action:
        return

    if user_id is None or action is None:
        # Only one of required argument is provided, probably a programmer error
        logger.error("Incorrect admin dialog call detected: user_id=%s, action=%s", user_id, action)
        return

    user_registry: UserRegistryAbstract = manager.middleware_data["user_registry"]
    await process_action(action, user_id, user_registry)
    # Dialog was called via a command, we close it instantly
    await manager.done()


async def on_process_result(_: Any, result: dict[str, Any] | None, manager: DialogManager):
    if result is None:
        return
    user_id: int | None = result.get("user_id")
    assert user_id is not None, "No user id found in resulting dictionary"
    action: ActionWithUser = manager.dialog_data["action"]
    user_registry: UserRegistryAbstract = manager.middleware_data["user_registry"]
    await process_action(action, user_id, user_registry)


async def user_action_handler(
        callback: CallbackQuery,
        _widget: Button,
        manager: DialogManager,
        action: ActionWithUser,
):
    manager.dialog_data["action"] = action

    if not has_admin_privileges(manager):
        i18n: TranslatorRunner = manager.middleware_data["i18n"]
        logger.info("Action %s is blocked for user %d", action, current_user_id(manager))
        await callback.answer(i18n.get("notify-forbidden"))
        await manager.done()
        return

    await manager.start(UserSelectionStates.START)


start_window = Window(
    FluentFormat("dialog-admin-main"),
    Row(
        Button(
            FluentFormat("dialog-admin-main.plus-admin"),
            id="plus_admin",
            on_click=partial(user_action_handler, action=ActionWithUser.GRANT_ADMIN),
        ),
        Button(
            FluentFormat("dialog-admin-main.minus-admin"),
            id="minus_admin",
            on_click=partial(user_action_handler, action=ActionWithUser.GRANT_ADMIN),
        ),
    ),
    Row(
        Button(
            FluentFormat("dialog-admin-main.plus-ban"),
            id="plus_ban",
            on_click=partial(user_action_handler, action=ActionWithUser.BAN_USER),
        ),
        Button(
            FluentFormat("dialog-admin-main.minus-ban"),
            id="minus_ban",
            on_click=partial(user_action_handler, action=ActionWithUser.UNBAN_USER),
        ),
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=AdministrationStates.START,
)


dialog = Dialog(
    start_window,
    on_start=on_dialog_start,
    on_process_result=on_process_result,
    name=__file__,
)