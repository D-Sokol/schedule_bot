import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel

from .custom_widgets import FluentFormat
from .states import SettingsStates

logger = logging.getLogger(__name__)


start_window = Window(
    FluentFormat("dialog-settings"),
    Cancel(FluentFormat("dialog-cancel")),
    state=SettingsStates.START,
)


dialog = Dialog(
    start_window,
    name=__name__,
)
