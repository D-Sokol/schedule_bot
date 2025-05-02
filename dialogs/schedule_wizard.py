import logging

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel, ListGroup, Button, Row
from aiogram_dialog.widgets.text import Format

from .states import ScheduleWizardStates
from .utils import FluentFormat


logger = logging.getLogger(__file__)


async def fake_data_getter(**_):
    entries = [
        {"id": 1, "dow": 1, "time": "17:00"},
        {"id": 2, "dow": 1, "time": "18:00"},
    ]
    return {
        "entries": entries,
    }


start_window = Window(
    FluentFormat("dialog-wizard-start"),
    ListGroup(
        Row(
            Button(Format("{item[dow]}"), "dow", on_click=None),
            Button(Format("{item[time]}"), "time", on_click=None),
        ),
        id="entries",
        item_id_getter=lambda item: item["id"],
        items="entries",
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleWizardStates.START,
    getter=fake_data_getter,
)


dialog = Dialog(
    start_window,
    name=__file__,
)