import logging
from typing import Any, TypedDict

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Cancel, ListGroup, Button, Row
from aiogram_dialog.widgets.text import Format
from fluentogram import TranslatorRunner
from magic_filter import F

from services.renderer.weekdays import Schedule, Entry, Time, WeekDay
from .states import ScheduleWizardStates
from .utils import FluentFormat


logger = logging.getLogger(__file__)


class EntryRepresentation(TypedDict):
    id: int
    dow: int
    hour: int
    minute: int
    description: str
    tags: list[str]


def _save_entries(manager: DialogManager, entries: list[EntryRepresentation], update_ids: bool = True):
    if update_ids:
        for i, entry in enumerate(entries):
            entry["id"] = i
    manager.dialog_data["entries"] = entries


async def on_dialog_start(start_data: dict[str, Any] | None, manager: DialogManager):
    entries: list[EntryRepresentation] = [
        {"id": 0, "dow": 1, "hour": 17, "minute": 0, "description": "d1", "tags": []},
        {"id": 1, "dow": 1, "hour": 18, "minute": 0, "description": "d2", "tags": ["a"]},
    ]
    _save_entries(manager, entries, update_ids=False)


async def new_entry_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    last_entry = entries[-1].copy() if entries else {"id": 0, "dow": 1, "hour": 9, "minute": 0, "description": "..."}
    entries.append(last_entry)
    _save_entries(manager, entries)


async def sort_entries_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    entries.sort(key=lambda e: (e["dow"], e["hour"], e["minute"]))
    _save_entries(manager, entries)


async def print_schedule_handler(
    callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    entries_formatted = {dow: [] for dow in WeekDay}
    for e in entries:
        entries_formatted[WeekDay(e["dow"])].append(
            Entry(
                time=Time(hour=e["hour"], minute=e["minute"]),
                description=e["description"],
                tags=set(e["tags"]),
            )
        )
    schedule = Schedule(records=entries_formatted)

    i18n: TranslatorRunner = manager.middleware_data["i18n"]
    await callback.message.answer(i18n.get("notify-wizard-print", schedule=str(schedule)))
    manager.show_mode = ShowMode.SEND


async def confirm_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    await manager.done({"entries": entries})


entries_filter = F["dialog_data"]["entries"]


start_window = Window(
    FluentFormat("dialog-wizard-start"),
    ListGroup(
        Row(
            Button(FluentFormat("weekdays-by_id", day=F["item"]["dow"]), "dow", on_click=None),
            Button(Format("{item[hour]}:{item[minute]:02d}"), "time", on_click=None),
            Button(FluentFormat("dialog-wizard-start.n_tags", n_tags=F["item"]["tags"].len()), "tags", on_click=None),
            Button(Format("{item[description]}"), "desc", on_click=None),
            Button(FluentFormat("dialog-wizard-start.clone"), "clone", on_click=None),
            Button(FluentFormat("dialog-wizard-start.remove"), "remove", on_click=None),
        ),
        id="entries",
        item_id_getter=lambda item: item["id"],
        items=entries_filter,
    ),
    Row(
        Button(FluentFormat("dialog-wizard-start.new"), "new", on_click=new_entry_handler),
        Button(FluentFormat("dialog-wizard-start.sort"), "sort", on_click=sort_entries_handler, when=entries_filter),
        Button(
            FluentFormat("dialog-wizard-start.print"), "print", on_click=print_schedule_handler, when=entries_filter
        ),
        Button(FluentFormat("dialog-wizard-start.confirm"), "confirm", on_click=confirm_handler),
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleWizardStates.START,
)


dialog = Dialog(
    start_window,
    name=__file__,
    on_start=on_dialog_start,
)
