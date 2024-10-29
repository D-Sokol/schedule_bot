import logging
from aiogram.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Start

from .backgrounds import BackgroundsStates as BackgroundStates


logger = logging.getLogger(__file__)


class MainMenuStates(StatesGroup):
    START = State()


start_window = Window(
    Const("Main Menu"),
    Start(Const("Фоновые изображения"), id="manage_backgrounds", state=BackgroundStates.START),
    Button(Const("Создать расписание"), id="create_schedule"),
    Button(Const("Шаблон расписания"), id="manage_templates"),
    Button(Const("Накладываемые элементы"), id="manage_elements"),
    state=MainMenuStates.START,
    getter=None,
)

dialog = Dialog(start_window, name=__file__)
