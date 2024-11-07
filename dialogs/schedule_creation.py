import html
import logging
from typing import Any

from aiogram.filters.state import State, StatesGroup
from aiogram.types import Message
from aiogram_dialog import Dialog, Window, Data, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Cancel, Start
from aiogram_dialog.widgets.text import Const, Format
from magic_filter import F

from bot_registry import RegistryAbstract, ElementRecord
from bot_registry.texts import ScheduleRegistryAbstract, Schedule
from .upload_background import UploadBackgroundStates
from .backgrounds import BackgroundsStates, has_backgrounds_condition, can_upload_background_condition
from .utils import active_user_id


logger = logging.getLogger(__file__)


class ScheduleStates(StatesGroup):
    START = State()
    EXPECT_TEXT = State()
    FINISH = State()


has_preselected_background_condition = F["start_data"]["element"]
has_selected_background_condition = F["dialog_data"]["element"]


async def on_dialog_start(start_data: Data, manager: DialogManager):
    manager.dialog_data["element"] = element = start_data.get("element")
    logger.info("Start planning a schedule, has preselected background: %s", element is not None)
    initial_state = manager.current_context().state
    if element is None:
        assert initial_state == ScheduleStates.START, f"Misconfigured state setting: {initial_state}"
    else:
        assert initial_state == ScheduleStates.EXPECT_TEXT, f"Misconfigured state setting: {initial_state}"


async def saved_backs_getter(
        dialog_manager: DialogManager, registry: RegistryAbstract, **_
) -> dict[str, Any]:
    user_id = active_user_id(dialog_manager)
    assert user_id is not None, "Who passed global scope into creation dialog?!"
    n_items = await registry.get_elements_count(user_id)
    logger.debug("Getter: can select background from %d images", n_items)
    return {
        "n_backgrounds": n_items,
    }


async def previous_schedule_getter(
        dialog_manager: DialogManager, registry: ScheduleRegistryAbstract, **_
) -> dict[str, Any]:
    user_id = active_user_id(dialog_manager)
    assert user_id is not None, "Who passed global scope into creation dialog?!"

    user_last_schedule = await registry.get_last_schedule(user_id)
    global_last_schedule = await registry.get_last_schedule(None)
    if global_last_schedule is None:
        # A good example should be provided in DB, but we want to provide an example in any case
        global_last_schedule = "Пн 10:00 Бег\nПн 11:30 Отжимания\nПт 18:00 Сходить в бар"

    return {
        "user_last_schedule": html.escape(str(user_last_schedule)),
        "user_has_schedule": user_last_schedule is not None,
        "global_last_schedule": html.escape(str(global_last_schedule)),
    }


async def process_schedule_creation(
        _message: Message,
        _widget: Any,
        manager: DialogManager,
        data: tuple[Schedule, list[str]],
):
    schedule, unparsed = data
    if schedule:
        pass  # TODO: start a task
    else:
        pass  # TODO: emit warning
    await manager.switch_to(ScheduleStates.FINISH)


async def process_upload_new_background(_start_data: Data, result: Data, manager: DialogManager):
    if result is None:
        # User cancelled upload, nothing is changed
        return
    assert isinstance(result, dict), f"Wrong type {type(result)} returned from child dialog"
    new_record: ElementRecord = result.get("element")
    manager.dialog_data["element"] = new_record
    await manager.switch_to(ScheduleStates.EXPECT_TEXT)


start_window = Window(
    Const("Create schedule"),
    Const(
        "Для создания расписания нужно выбрать фон из списка сохраненных изображений или загрузить новый.",
    ),
    Start(
        Const("Выбрать фон"),
        id="select_background_from_schedule",
        state=BackgroundsStates.START,
        when=has_backgrounds_condition,
        data={"select_only": True, "global_scope": False},
    ),
    Start(
        Const("Загрузить новый фон"),
        id="upload_background_from_schedule",
        state=UploadBackgroundStates.START,
        when=can_upload_background_condition,
    ),
    Cancel(Const("❌ Отставеть!")),
    state=ScheduleStates.START,
    on_process_result=process_upload_new_background,
)

expect_input_window = Window(
    Const("Введите текст расписания"),
    Format(
        "Вот предыдущее использованное вами расписание:\n<i>{user_last_schedule}</i>",
        when=F["user_has_schedule"],
    ),
    Format(
        "Вот простой пример расписания:\n<i>{global_last_schedule}</i>",
        when=~F["user_has_schedule"],
    ),
    TextInput(
        id="schedule_text",
        type_factory=ScheduleRegistryAbstract.parse_schedule_text,
        on_success=process_schedule_creation,
    ),
    getter=previous_schedule_getter,
    state=ScheduleStates.EXPECT_TEXT,
)

finish_window = Window(
    Const("Thank you"),
    Cancel(Const("Хорошо.")),
    state=ScheduleStates.FINISH,
)


dialog = Dialog(start_window, expect_input_window, finish_window, on_start=on_dialog_start, name=__file__)
