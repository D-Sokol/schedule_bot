import logging
from aiogram.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button


logger = logging.getLogger(__file__)


class States(StatesGroup):
    START = State()


async def btn1_on_click(_: CallbackQuery, button: Button, manager: DialogManager) -> None:
    logger.info(await button.text.render_text({}, manager))


start_window = Window(
    Const("Useless window"),
    Button(Const("Button"), id="btn1", on_click=btn1_on_click),
    state=States.START,
    getter=None,
)

dialog = Dialog(start_window, name=__file__)
