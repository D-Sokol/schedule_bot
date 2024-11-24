import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Start

from .states import MainMenuStates, BackgroundsStates, ScheduleStates
from .utils import FluentFormat

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
    Button(FluentFormat("dialog-main.templates"), id="manage_templates"),
    Start(
        FluentFormat("dialog-main.backgrounds-local"),
        id="manage_elements",
        state=BackgroundsStates.START,
        data={"global_scope": True, "select_only": False},
    ),
    state=MainMenuStates.START,
)

dialog = Dialog(start_window, name=__file__)
