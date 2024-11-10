import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Start

from .states import MainMenuStates, BackgroundsStates, ScheduleStates

logger = logging.getLogger(__file__)


start_window = Window(
    Const("Main Menu"),
    Start(
        Const("Фоновые изображения"),
        id="manage_backgrounds",
        state=BackgroundsStates.START,
        data={"global_scope": False, "select_only": False},
    ),
    Start(Const("Создать расписание"), id="create_schedule", state=ScheduleStates.START),
    Button(Const("Шаблон расписания"), id="manage_templates"),
    Start(
        Const("Накладываемые элементы"),
        id="manage_elements",
        state=BackgroundsStates.START,
        data={"global_scope": True, "select_only": False},
    ),
    state=MainMenuStates.START,
)

dialog = Dialog(start_window, name=__file__)
