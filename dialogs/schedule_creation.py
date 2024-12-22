import html
import logging
from datetime import date, timedelta
from functools import partial
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, Data, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Cancel, Start, Button, SwitchTo, Calendar
from fluentogram import TranslatorRunner
from magic_filter import F

from bot_registry.texts import ScheduleRegistryAbstract, Schedule
from database_models import ImageAsset
from .backgrounds import has_backgrounds_condition, can_upload_background_condition, saved_backs_getter
from .states import ScheduleStates, BackgroundsStates, UploadBackgroundStates
from .utils import current_user_id, FluentFormat


logger = logging.getLogger(__file__)


has_preselected_background_condition = F["start_data"]["element"]
has_selected_background_condition = F["dialog_data"]["element"]


async def on_dialog_start(start_data: Data, manager: DialogManager):
    element = None
    if start_data:
        element = start_data.get("element")
    manager.dialog_data["element"] = element
    logger.info("Start planning a schedule, has preselected background: %s", element is not None)
    initial_state = manager.current_context().state
    if element is None:
        assert initial_state == ScheduleStates.START, f"Misconfigured state setting: {initial_state}"
    else:
        assert initial_state == ScheduleStates.EXPECT_TEXT, f"Misconfigured state setting: {initial_state}"


async def process_date_selected(
        _callback: CallbackQuery,
        _widget: Any,
        manager: DialogManager,
        selected_date: date,
):
    user_id = current_user_id(manager)
    schedule_registry: ScheduleRegistryAbstract = manager.middleware_data["schedule_registry"]
    logger.info("Selected date: %s", selected_date.isoformat())
    schedule: Schedule = manager.dialog_data["schedule"]
    element: ImageAsset = manager.dialog_data["element"]
    _ = selected_date, schedule, element  # TODO: push task
    await schedule_registry.update_last_schedule(user_id, schedule)
    await manager.switch_to(ScheduleStates.FINISH)


async def previous_schedule_getter(
        dialog_manager: DialogManager,
        schedule_registry: ScheduleRegistryAbstract,
        i18n: TranslatorRunner,
        **_
) -> dict[str, Any]:
    user_id = current_user_id(dialog_manager)

    user_last_schedule = await schedule_registry.get_last_schedule(user_id)
    global_last_schedule = await schedule_registry.get_last_schedule(None)
    if global_last_schedule is None:
        # A good example should be provided in DB, but we want to provide an example in any case
        global_last_schedule = i18n.get("dialog-schedule-text.example")

    return {
        "user_last_schedule": html.escape(str(user_last_schedule)),
        "user_has_schedule": user_last_schedule is not None,
        "global_last_schedule": html.escape(str(global_last_schedule)),
    }


async def process_schedule_creation(
        message: Message,
        _widget: Any,
        manager: DialogManager,
        data: str,
):
    i18n: TranslatorRunner = manager.middleware_data["i18n"]
    schedule_registry: ScheduleRegistryAbstract = manager.middleware_data["schedule_registry"]
    schedule, unparsed = schedule_registry.parse_schedule_text(data)
    if schedule.is_empty():
        await message.answer(i18n.get("dialog-schedule-text.warn_empty"))
        return
    elif unparsed:
        answer = "\n".join(
            [i18n.get("dialog-schedule-text.warn_unparsed"), *unparsed]
        )
        await message.answer(answer)
    manager.dialog_data["schedule"] = schedule
    await manager.switch_to(ScheduleStates.EXPECT_DATE)


async def process_upload_new_background(_start_data: Data, result: Data, manager: DialogManager):
    if result is None:
        # User cancelled upload, nothing is changed
        return
    assert isinstance(result, dict), f"Wrong type {type(result)} returned from child dialog"
    new_record: ImageAsset = result.get("element")
    manager.dialog_data["element"] = new_record
    await manager.switch_to(ScheduleStates.EXPECT_TEXT)


start_window = Window(
    FluentFormat("dialog-schedule-main"),
    Start(
        FluentFormat("dialog-schedule-main.select"),
        id="select_background_from_schedule",
        state=BackgroundsStates.START,
        when=has_backgrounds_condition,
        data={"select_only": True, "global_scope": False},
    ),
    Start(
        FluentFormat("dialog-schedule-main.upload"),
        id="upload_background_from_schedule",
        state=UploadBackgroundStates.START,
        when=can_upload_background_condition,
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleStates.START,
    on_process_result=process_upload_new_background,
    getter=partial(saved_backs_getter, _only_count=True),
)

expect_input_window = Window(
    FluentFormat("dialog-schedule-text.presented", when=F["user_has_schedule"]),
    FluentFormat("dialog-schedule-text.missing", when=~F["user_has_schedule"]),
    Cancel(FluentFormat("dialog-cancel")),
    TextInput(id="schedule_text", on_success=process_schedule_creation),
    getter=previous_schedule_getter,
    state=ScheduleStates.EXPECT_TEXT,
)


async def process_this_week(callback: CallbackQuery, widget: Button, manager: DialogManager):
    today = date.today()
    return await process_date_selected(callback, widget, manager, today)


async def process_next_week(callback: CallbackQuery, widget: Button, manager: DialogManager):
    next_week = date.today() + timedelta(days=7)
    return await process_date_selected(callback, widget, manager, next_week)


expect_date_window = Window(
    FluentFormat("dialog-schedule-date"),
    Button(FluentFormat("dialog-schedule-date.this"), id="this_week", on_click=process_this_week),
    Button(FluentFormat("dialog-schedule-date.next"), id="next_week", on_click=process_next_week),
    SwitchTo(FluentFormat("dialog-schedule-date.custom"), id="other_date", state=ScheduleStates.EXPECT_DATE_CALENDAR),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleStates.EXPECT_DATE,
)

expect_date_calendar_window = Window(
    FluentFormat("dialog-schedule-calendar"),
    SwitchTo(FluentFormat("dialog-schedule-calendar.back"), id="back", state=ScheduleStates.EXPECT_DATE),
    Calendar(id="calendar", on_click=process_date_selected),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleStates.EXPECT_DATE_CALENDAR,
)

finish_window = Window(
    FluentFormat("dialog-schedule-finish"),
    Cancel(FluentFormat("dialog-schedule-finish.return")),
    state=ScheduleStates.FINISH,
)


dialog = Dialog(
    start_window,
    expect_input_window,
    expect_date_window,
    expect_date_calendar_window,
    finish_window,
    on_start=on_dialog_start,
    name=__file__,
)
