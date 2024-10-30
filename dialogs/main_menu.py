import logging
from aiogram.filters.state import State, StatesGroup

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Start

from .backgrounds import BackgroundsStates


logger = logging.getLogger(__file__)


class MainMenuStates(StatesGroup):
    START = State()


start_window = Window(
    Const("Main Menu"),
    Start(Const("Фоновые изображения"), id="manage_backgrounds", state=BackgroundsStates.START),
    Button(Const("Создать расписание"), id="create_schedule"),
    Button(Const("Шаблон расписания"), id="manage_templates"),
    Button(Const("Накладываемые элементы"), id="manage_elements"),
    state=MainMenuStates.START,
)

dialog = Dialog(start_window, name=__file__)
