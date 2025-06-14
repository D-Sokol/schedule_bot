import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.api.entities import LaunchMode
from aiogram_dialog.widgets.kbd import Button, Start
from .states import MainMenuStates, BackgroundsStates, ScheduleStates, TemplatesStates, AdministrationStates
from .utils import FluentFormat, handler_not_implemented_button, has_admin_privileges_filter

logger = logging.getLogger(__name__)


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
    Start(
        FluentFormat("dialog-main.backgrounds-global"),
        id="manage_elements",
        state=BackgroundsStates.START,
        data={"global_scope": True, "select_only": False},
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

dialog = Dialog(start_window, name=__name__, launch_mode=LaunchMode.ROOT)
