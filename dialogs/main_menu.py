import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Start

from .states import MainMenuStates, BackgroundsStates, ScheduleStates, TemplatesStates
from .utils import FluentFormat, handler_not_implemented_button

logger = logging.getLogger(__file__)


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
    ),
    Button(
        FluentFormat("dialog-main.settings"),
        id="user_settings",
        on_click=handler_not_implemented_button,
    ),
    state=MainMenuStates.START,
)

dialog = Dialog(start_window, name=__file__)
