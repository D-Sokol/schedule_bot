import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Cancel
from .states import UserSelectionStates
from .utils import FluentFormat


logger = logging.getLogger(__file__)


start_window = Window(
    Const("select"),
    Cancel(FluentFormat("dialog-cancel")),
    state=UserSelectionStates.START,
)


dialog = Dialog(
    start_window,
    name=__file__,
)
