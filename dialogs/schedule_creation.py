import asyncio
import html
import logging
from datetime import date, timedelta
from functools import partial
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, Data, DialogManager, ShowMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Cancel, Start, Button, SwitchTo, Calendar
from fluentogram import TranslatorRunner
from magic_filter import F

from bot_registry import TemplateRegistryAbstract
from bot_registry.texts import ScheduleRegistryAbstract, Schedule
from .backgrounds import has_backgrounds_condition, can_upload_background_condition, saved_backs_getter
from .states import ScheduleStates, BackgroundsStates, UploadBackgroundStates
from .utils import current_user_id, current_chat_id, FluentFormat, handler_not_implemented_button

logger = logging.getLogger(__file__)


has_preselected_background_condition = F["start_data"]["element_id"]
has_selected_background_condition = F["dialog_data"]["element_id"]


async def on_dialog_start(start_data: Data, manager: DialogManager):
    assert start_data is None or isinstance(start_data, dict)
    element_id: str | None = None
    if start_data:
        element_id: str = start_data.get("element_id")
    manager.dialog_data["element_id"] = element_id
    logger.info("Start planning a schedule, has preselected background: %s", element_id is not None)
    initial_state = manager.current_context().state
    if element_id is None:
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
    chat_id = current_chat_id(manager)
    schedule_registry: ScheduleRegistryAbstract = manager.middleware_data["schedule_registry"]
    template_registry: TemplateRegistryAbstract = manager.middleware_data["template_registry"]
    result_date = selected_date - timedelta(days=selected_date.weekday())  # First day of selected week (always Monday)
    logger.info("Selected date: %s, start of week: %s", selected_date.isoformat(), result_date.isoformat())
    schedule: Schedule = manager.dialog_data["schedule"]
    element_id: str = manager.dialog_data["element_id"]
    template = (await template_registry.get_template(user_id)) or (await template_registry.get_template(None))
    if template is None:
        logger.error("No template for user %d and global template is also missing!", user_id)
        return
    await asyncio.gather(
        schedule_registry.render_schedule(user_id, chat_id, schedule, element_id, template, result_date),
        schedule_registry.update_last_schedule(user_id, schedule)
    )
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
        logger.warning("Global last schedule is missing. Text from locales file will be used instead")
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
    assert result.get("element_id") is not None, "No element id found in resulting dictionary!"
    manager.dialog_data["element_id"] = result["element_id"]
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
        data={"global_scope": False},
        when=can_upload_background_condition,
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleStates.START,
    on_process_result=process_upload_new_background,
    getter=partial(saved_backs_getter, _only_count=True),
)

async def process_accept_previous(_callback: CallbackQuery, _widget: Button, manager: DialogManager):
    user_id = current_user_id(manager)
    schedule_registry: ScheduleRegistryAbstract = manager.middleware_data["schedule_registry"]

    schedule = await schedule_registry.get_last_schedule(user_id)
    assert schedule is not None and not schedule.is_empty(), "Displaying button error"
    manager.dialog_data["schedule"] = schedule


expect_input_window = Window(
    FluentFormat("dialog-schedule-text.presented", when=F["user_has_schedule"]),
    FluentFormat("dialog-schedule-text.missing", when=~F["user_has_schedule"]),
    SwitchTo(
        FluentFormat("dialog-schedule-text.accept_previous"),
        id="accept_prev",
        state=ScheduleStates.EXPECT_DATE,
        on_click=process_accept_previous,
        when=F["user_has_schedule"],
    ),
    Button(
        FluentFormat("dialog-schedule-text.wizard"),
        id="enter_wizard",
        on_click=handler_not_implemented_button,
    ),
    SwitchTo(FluentFormat("dialog-schedule-text.back"), id="back", state=ScheduleStates.START),
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
    SwitchTo(FluentFormat("dialog-schedule-date.back"), id="back", state=ScheduleStates.EXPECT_TEXT),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleStates.EXPECT_DATE,
)

expect_date_calendar_window = Window(
    FluentFormat("dialog-schedule-calendar"),
    Calendar(id="calendar", on_click=process_date_selected),
    SwitchTo(FluentFormat("dialog-schedule-calendar.back"), id="back", state=ScheduleStates.EXPECT_DATE),
    Cancel(FluentFormat("dialog-cancel")),
    state=ScheduleStates.EXPECT_DATE_CALENDAR,
)

finish_window = Window(
    FluentFormat("dialog-schedule-finish"),
    Cancel(FluentFormat("dialog-schedule-finish.return"), show_mode=ShowMode.DELETE_AND_SEND),
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
