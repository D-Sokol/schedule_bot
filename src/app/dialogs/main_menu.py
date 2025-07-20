import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.api.entities import LaunchMode
from aiogram_dialog.widgets.kbd import Start

from .backgrounds import START_DATA_GLOBAL_SCOPE_KEY, START_DATA_SELECT_ONLY_KEY
from .custom_widgets import FluentFormat
from .states import (
    AdministrationStates,
    BackgroundsStates,
    MainMenuStates,
    ScheduleStates,
    SettingsStates,
    TemplatesStates,
)
from .utils import has_admin_privileges_filter

logger = logging.getLogger(__name__)


start_window = Window(
    FluentFormat("dialog-main"),
    Start(
        FluentFormat("dialog-main.backgrounds-local"),
        id="manage_backgrounds",
        state=BackgroundsStates.START,
        data={START_DATA_GLOBAL_SCOPE_KEY: False, START_DATA_SELECT_ONLY_KEY: False},
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
        data={START_DATA_GLOBAL_SCOPE_KEY: True, START_DATA_SELECT_ONLY_KEY: False},
        when=has_admin_privileges_filter,
    ),
    Start(
        FluentFormat("dialog-main.admin"),
        id="admin",
        state=AdministrationStates.START,
        when=has_admin_privileges_filter,
    ),
    Start(
        FluentFormat("dialog-main.settings"),
        id="user_settings",
        state=SettingsStates.START,
    ),
    state=MainMenuStates.START,
)

dialog = Dialog(start_window, name=__name__, launch_mode=LaunchMode.ROOT)
