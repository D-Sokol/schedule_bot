import logging
from enum import StrEnum
from functools import partial
from typing import Any

from aiogram.types import CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Cancel, Row
from fluentogram import TranslatorRunner

from app.middlewares.i18n import I18N_KEY
from app.middlewares.registry import USER_REGISTRY_KEY
from bot_registry import UserRegistryAbstract
from .custom_widgets import FluentFormat
from .states import AdministrationStates, UserSelectionStates
from .utils import current_user_id, has_admin_privileges


logger = logging.getLogger(__name__)

MIDDLEWARE_PRIMARY_ADMIN_ID_KEY = "primary_admin_id"
DIALOG_ACTION_KEY = "action"
START_DATA_USER_ID_KEY = "user_id"
START_DATA_ACTION_KEY = "action"


class ActionWithUser(StrEnum):
    GRANT_ADMIN = "grant_admin"
    REVOKE_ADMIN = "revoke_admin"
    BAN_USER = "ban_user"
    UNBAN_USER = "unban_user"


async def process_action(action: ActionWithUser, user_tg_id: int, user_registry: UserRegistryAbstract):
    match action:
        case ActionWithUser.GRANT_ADMIN:
            await user_registry.grant_admin(user_tg_id)
        case ActionWithUser.REVOKE_ADMIN:
            await user_registry.revoke_admin(user_tg_id)
        case ActionWithUser.BAN_USER:
            await user_registry.ban_user(user_tg_id)
        case ActionWithUser.UNBAN_USER:
            await user_registry.unban_user(user_tg_id)
        case _:
            logger.error("Unknown action %s", action)


async def report_action_done(action: ActionWithUser, user_tg_id: int, manager: DialogManager):
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    match action:
        case ActionWithUser.GRANT_ADMIN:
            await manager.event.answer(i18n.get("notify-admin.grant", user_id=user_tg_id))
        case ActionWithUser.REVOKE_ADMIN:
            await manager.event.answer(i18n.get("notify-admin.revoke", user_id=user_tg_id))
        case ActionWithUser.BAN_USER:
            await manager.event.answer(i18n.get("notify-admin.ban", user_id=user_tg_id))
        case ActionWithUser.UNBAN_USER:
            await manager.event.answer(i18n.get("notify-admin.unban", user_id=user_tg_id))
        case _:
            logger.error("Unknown action %s", action)


async def on_dialog_start(start_data: dict[str, Any] | None, manager: DialogManager):
    if start_data is None:
        return

    user_id: int | None = start_data.get(START_DATA_USER_ID_KEY)
    action: ActionWithUser | None = start_data.get(START_DATA_ACTION_KEY)
    if user_id is None is action:
        return

    if user_id is None:
        manager.dialog_data[DIALOG_ACTION_KEY] = action
        await manager.start(UserSelectionStates.START)
        return

    if action is None:
        # user id provided without an action to perform, must be a programmer error.
        logger.error("Incorrect admin dialog call detected: user_id=%s, action=%s", user_id, action)
        return

    user_registry: UserRegistryAbstract = manager.middleware_data[USER_REGISTRY_KEY]
    if not has_admin_privileges(manager):
        logger.info("Refuse to perform action %s(%d) for user %d", action, user_id, current_user_id(manager))
        return
    if action in {ActionWithUser.REVOKE_ADMIN, ActionWithUser.BAN_USER} and user_id == manager.middleware_data.get(
        MIDDLEWARE_PRIMARY_ADMIN_ID_KEY
    ):
        logger.info("Refuse to perform action %s for user %d to primary admin", action, current_user_id(manager))
        return

    await process_action(action, user_id, user_registry)
    await report_action_done(action, user_id, manager)
    # Dialog was called via a command, we close it instantly
    await manager.done()


async def on_process_result(_: Any, result: dict[str, Any] | None, manager: DialogManager):
    if result is None:
        return
    user_id: int | None = result.get(START_DATA_USER_ID_KEY)
    assert user_id is not None, "No user id found in resulting dictionary"
    action: ActionWithUser = manager.dialog_data[DIALOG_ACTION_KEY]
    user_registry: UserRegistryAbstract = manager.middleware_data[USER_REGISTRY_KEY]
    if not has_admin_privileges(manager):
        logger.info("Refuse to perform action %s(%d) for user %d", action, user_id, current_user_id(manager))
        return
    if action in {ActionWithUser.REVOKE_ADMIN, ActionWithUser.BAN_USER} and user_id == manager.middleware_data.get(
        MIDDLEWARE_PRIMARY_ADMIN_ID_KEY
    ):
        logger.info("Refuse to perform action %s for user %d to primary admin", action, current_user_id(manager))
        return

    await process_action(action, user_id, user_registry)
    await report_action_done(action, user_id, manager)


async def user_action_handler(
    callback: CallbackQuery,
    _widget: Button,
    manager: DialogManager,
    action: ActionWithUser,
):
    manager.dialog_data[DIALOG_ACTION_KEY] = action

    if not has_admin_privileges(manager):
        i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
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
    name=__name__,
)
