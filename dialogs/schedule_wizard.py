import logging
from typing import Any, TypedDict

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Cancel, ListGroup, Button, Row
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from .states import ScheduleWizardStates
from .utils import FluentFormat


logger = logging.getLogger(__file__)


class EntryRepresentation(TypedDict):
    id: int
    dow: int
    time: str
    description: str


async def on_dialog_start(start_data: dict[str, Any] | None, manager: DialogManager):
    entries: list[EntryRepresentation] = [
        {"id": 1, "dow": 1, "time": "17:00", "description": "d1"},
        {"id": 2, "dow": 1, "time": "18:00", "description": "d2"},
    ]
    manager.dialog_data["entries"] = entries


start_window = Window(
    FluentFormat("dialog-wizard-start"),
    ListGroup(
        Row(
            Button(Format("{item[dow]}"), "dow", on_click=None),
            Button(Format("{item[time]}"), "time", on_click=None),
            Button(Format("{item[description]}"), "desc", on_click=None),
            Button(FluentFormat("dialog-wizard-start.clone"), "clone", on_click=None),
            Button(FluentFormat("dialog-wizard-start.remove"), "remove", on_click=None),
        ),
        id="entries",
        item_id_getter=lambda item: item["id"],
        items=F["dialog_data"]["entries"],
    ),
    Row(
        Button(FluentFormat("dialog-wizard-start.new"), "new"),
        Button(FluentFormat("dialog-wizard-start.sort"), "sort"),
        Button(FluentFormat("dialog-wizard-start.print"), "print"),
        Button(FluentFormat("dialog-wizard-start.confirm"), "confirm"),
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleWizardStates.START,
)


dialog = Dialog(
    start_window,
    name=__file__,
    on_start=on_dialog_start,
)
