import logging
import re
from typing import Any, TypedDict

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode, SubManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Cancel, ListGroup, Button, Row, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Format
from fluentogram import TranslatorRunner
from magic_filter import F

from services.renderer.weekdays import Schedule, Entry, Time, WeekDay
from .states import ScheduleWizardStates
from .custom_widgets import FluentFormat


logger = logging.getLogger(__name__)


class EntryRepresentation(TypedDict):
    id: int
    dow: int  # 1-based
    hour: int
    minute: int
    description: str
    tags: list[str]


TEMPLATE_ENTITY: EntryRepresentation = {"id": 0, "dow": 1, "hour": 9, "minute": 0, "description": "...", "tags": []}


def _save_entries(manager: DialogManager, entries: list[EntryRepresentation], update_ids: bool = True):
    if update_ids:
        for i, entry in enumerate(entries):
            entry["id"] = i
    manager.dialog_data["entries"] = entries


async def on_dialog_start(start_data: dict[str, Any] | None, manager: DialogManager):
    if not start_data:
        entries: list[EntryRepresentation] = []
    else:
        entries = start_data.get("entries", [])
    _save_entries(manager, entries, update_ids=False)


async def new_entry_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    last_entry = entries[-1].copy() if entries else TEMPLATE_ENTITY.copy()
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


async def store_selected_item(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    assert isinstance(manager, SubManager)
    manager.dialog_data["item_id"] = int(manager.item_id)


async def clone_selected_item_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    assert isinstance(manager, SubManager)
    index = int(manager.item_id)
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    cloned_entry = entries[index].copy()
    entries.insert(index, cloned_entry)
    _save_entries(manager, entries)


async def remove_selected_item_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    assert isinstance(manager, SubManager)
    index = int(manager.item_id)
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    del entries[index]
    _save_entries(manager, entries)


entries_filter = F["dialog_data"]["entries"]
# Note: `F["x"][F["y"]]` is equivalent to `d["x"] if d["y"] else None`, not the expected thing.
current_entry_filter = F["dialog_data"].func(lambda dd: dd["entries"][dd["item_id"]])


start_window = Window(
    FluentFormat("dialog-wizard-start"),
    ScrollingGroup(
        ListGroup(
            Row(
                SwitchTo(
                    FluentFormat("weekdays-by_id", day=F["item"]["dow"]),
                    "dow",
                    state=ScheduleWizardStates.SELECT_DOW,
                    on_click=store_selected_item,
                ),
                SwitchTo(
                    Format("{item[hour]}:{item[minute]:02d}"),
                    "time",
                    state=ScheduleWizardStates.SELECT_TIME,
                    on_click=store_selected_item,
                ),
                SwitchTo(
                    FluentFormat("dialog-wizard-start.n_tags", n_tags=F["item"]["tags"].len()),
                    "tags",
                    state=ScheduleWizardStates.SELECT_TAGS,
                    on_click=store_selected_item,
                ),
                SwitchTo(
                    Format("{item[description]}"),
                    "desc",
                    state=ScheduleWizardStates.SELECT_DESC,
                    on_click=store_selected_item,
                ),
                Button(FluentFormat("dialog-wizard-start.clone"), "clone", on_click=clone_selected_item_handler),
                Button(FluentFormat("dialog-wizard-start.remove"), "remove", on_click=remove_selected_item_handler),
            ),
            id="entries",
            item_id_getter=lambda item: item["id"],
            items=entries_filter,
        ),
        id="entries_sg",
        height=7,
        when=entries_filter,
        hide_on_single_page=True,
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


async def update_item_dow_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
    dow_id: str,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    index: int = manager.dialog_data["item_id"]
    dow_value = int(dow_id)
    assert dow_value in range(1, 8)
    entries[index]["dow"] = dow_value
    _save_entries(manager, entries, update_ids=False)
    await manager.switch_to(ScheduleWizardStates.START)


dow_window = Window(
    FluentFormat("dialog-wizard-dow", current_day=current_entry_filter["dow"]),
    Select(
        FluentFormat("weekdays-by_id", day=F["item"]),
        "dow_select",
        item_id_getter=lambda x: x,
        items=range(1, 8),
        on_click=update_item_dow_handler,
    ),
    SwitchTo(FluentFormat("dialog-wizard-dow.back"), "back", ScheduleWizardStates.START),
    state=ScheduleWizardStates.SELECT_DOW,
)


_time_regex = re.compile(r"(\d+)[\s:.](\d+)")


def time_type_factory(s: str) -> tuple[int, int]:
    match = _time_regex.fullmatch(s)
    if match is None:
        raise ValueError
    hour, minute = match.groups()
    return int(hour), int(minute)


async def update_item_time_handler(
    _message: Message,
    _widget: Any,
    manager: DialogManager,
    time: tuple[int, int],
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    index: int = manager.dialog_data["item_id"]
    hour, minute = time
    entries[index]["hour"] = hour
    entries[index]["minute"] = minute
    _save_entries(manager, entries, update_ids=False)
    await manager.switch_to(ScheduleWizardStates.START)


time_window = Window(
    FluentFormat(
        "dialog-wizard-time", current_time=current_entry_filter.func(lambda e: f"{e['hour']}:{e['minute']:02d}")
    ),
    SwitchTo(FluentFormat("dialog-wizard-time.back"), "back", ScheduleWizardStates.START),
    TextInput("inp_time", type_factory=time_type_factory, on_success=update_item_time_handler),
    state=ScheduleWizardStates.SELECT_TIME,
)


async def update_item_tags_handler(
    _message: Message,
    _widget: Any,
    manager: DialogManager,
    tags_str: str,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    index: int = manager.dialog_data["item_id"]
    tags = tags_str.split(",")
    tags = [tag.strip() for tag in tags]
    entries[index]["tags"] = tags
    _save_entries(manager, entries, update_ids=False)
    await manager.switch_to(ScheduleWizardStates.START)


async def update_item_clear_tags_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    index: int = manager.dialog_data["item_id"]
    entries[index]["tags"] = []
    _save_entries(manager, entries, update_ids=False)
    await manager.switch_to(ScheduleWizardStates.START)


tags_window = Window(
    FluentFormat(
        "dialog-wizard-tags",
        n_tags=current_entry_filter["tags"].len(),
        current_tags=current_entry_filter["tags"].func(", ".join),
    ),
    Button(FluentFormat("dialog-wizard-tags.clear"), "no_tags", on_click=update_item_clear_tags_handler),
    SwitchTo(FluentFormat("dialog-wizard-tags.back"), "back", ScheduleWizardStates.START),
    TextInput("inp_tags", on_success=update_item_tags_handler),
    state=ScheduleWizardStates.SELECT_TAGS,
)


async def update_item_desc_handler(
    _message: Message,
    _widget: Any,
    manager: DialogManager,
    description: str,
) -> None:
    entries: list[EntryRepresentation] = manager.dialog_data["entries"]
    index: int = manager.dialog_data["item_id"]
    entries[index]["description"] = description
    _save_entries(manager, entries, update_ids=False)
    await manager.switch_to(ScheduleWizardStates.START)


desc_window = Window(
    FluentFormat("dialog-wizard-desc", current_desc=current_entry_filter["description"]),
    SwitchTo(FluentFormat("dialog-wizard-desc.back"), "back", ScheduleWizardStates.START),
    TextInput("inp_desc", on_success=update_item_desc_handler),
    state=ScheduleWizardStates.SELECT_DESC,
)


dialog = Dialog(
    start_window,
    dow_window,
    time_window,
    tags_window,
    desc_window,
    name=__name__,
    on_start=on_dialog_start,
)
