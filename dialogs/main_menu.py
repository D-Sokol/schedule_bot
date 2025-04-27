import logging
from typing import cast

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.api.entities import LaunchMode
from aiogram_dialog.widgets.kbd import Button, Start
from fluentogram import TranslatorRunner

from database_models import User
from .states import MainMenuStates, BackgroundsStates, ScheduleStates, TemplatesStates
from .utils import FluentFormat, handler_not_implemented_button, has_admin_privileges_filter

logger = logging.getLogger(__file__)


async def start_background_global(callback: CallbackQuery, _button: Button, manager: DialogManager):
    user = cast(User, manager.middleware_data["user"])
    logging.debug("Checking before opening backgrounds with global scope for user %d", user.tg_id)
    if not user.is_admin:
        logger.info("Editing global scope assets is blocked for user %d", user.tg_id)
        i18n: TranslatorRunner = manager.middleware_data["i18n"]
        await callback.answer(i18n.get("notify-forbidden"))
        return
    logger.debug("Editing global scope assets is allowed for user %d", user.tg_id)
    await manager.start(BackgroundsStates.START, data={"global_scope": True, "select_only": False})


start_window = Window(
    FluentFormat("dialog-main"),
    Start(
        FluentFormat("dialog-main.backgrounds-local"),
        id="manage_backgrounds",
        state=BackgroundsStates.START,
        data={"global_scope": False, "select_only": False},
    ),
    Start(FluentFormat("dialog-main.create"), id="create_schedule", state=ScheduleStates.START),
    Start(
        FluentFormat("dialog-main.templates"),
        id="manage_templates",
        state=TemplatesStates.START,
    ),
    Button(
        FluentFormat("dialog-main.backgrounds-global"),
        id="manage_elements",
        on_click=start_background_global,
        when=has_admin_privileges_filter,
    ),
    Start(
        FluentFormat("dialog-main.admin"),
        id="admin",
        state=AdministrationStates.START,
        when=has_admin_privileges_filter,
    ),
    Button(
        FluentFormat("dialog-main.settings"),
        id="user_settings",
        on_click=handler_not_implemented_button,
    ),
    state=MainMenuStates.START,
)

dialog = Dialog(start_window, name=__file__, launch_mode=LaunchMode.ROOT)
