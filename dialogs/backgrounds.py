import html
import logging
from pathlib import Path
from typing import Any, cast

from aiogram.filters.state import State, StatesGroup
from aiogram.types import ContentType, CallbackQuery, BufferedInputFile

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId, ShowMode
from aiogram_dialog.widgets.text import Const, Format, Case
from aiogram_dialog.widgets.kbd import Button, Start, Cancel, Select, SwitchTo, ScrollingGroup
from aiogram_dialog.widgets.media import DynamicMedia
from magic_filter import F, MagicFilter

from elements_registry import ElementsRegistryAbstract
from .upload_background import UploadBackgroundStates
from .utils import not_implemented_button_handler


logger = logging.getLogger(__file__)


BACKGROUNDS_LIMIT = 6
FILE_SIZE_LIMIT = 10 * 1024 * 1024

FILE_SIZE_ERROR_REASON = "file_size"
UNREADABLE_ERROR_REASON = "unreadable"


class BackgroundsStates(StatesGroup):
    START = State()
    SELECTED_IMAGE = State()


async def saved_backs_getter(elements_registry: ElementsRegistryAbstract, **_) -> dict[str, Any]:
    items = await elements_registry.get_elements(None)  # TODO: user_id
    backgrounds_limit = BACKGROUNDS_LIMIT
    logger.debug("Getter: %d images found with limit %d", len(items), backgrounds_limit)
    return {
        "items": items,
        "n_backgrounds": len(items),
        "limit": backgrounds_limit,
    }


async def selected_image_getter(dialog_manager: DialogManager, **_) -> dict[str, Any]:
    file_name: str = dialog_manager.dialog_data["file_name"]
    file_id: str = dialog_manager.dialog_data["file_id_photo"]
    if file_id is None:
        raise NotImplementedError  # TODO: send content as photo
    return {
        "background": MediaAttachment(ContentType.PHOTO, file_id=MediaId(file_id)),
        "escaped_name": html.escape(file_name),
    }


async def select_image_handler(
        _callback: CallbackQuery,
        _widget: Any,
        manager: DialogManager,
        item_id: str,
):
    elements_registry: ElementsRegistryAbstract = manager.middleware_data["elements_registry"]
    element = await elements_registry.get_element(None, int(item_id))
    manager.dialog_data["file_id_photo"] = element.file_id_photo
    manager.dialog_data["file_id_document"] = element.file_id_document
    manager.dialog_data["file_name"] = element.name
    manager.dialog_data["element_id"] = element.id
    logger.debug("Getter: selected image %s, id %s", element.name, item_id)
    await manager.switch_to(BackgroundsStates.SELECTED_IMAGE)


async def send_full_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    file_name: str = manager.dialog_data["file_name"]
    file_id: str = manager.dialog_data["file_id_document"]
    if file_id is not None:
        logger.debug("Sending full version for image %s", file_name)
        await callback.message.answer_document(document=file_id, caption=html.escape(file_name))
    else:
        user_id = None  # TODO: user_id
        element_id = manager.dialog_data["element_id"]
        elements_registry: ElementsRegistryAbstract = manager.middleware_data["elements_registry"]
        logger.info("Sending image %s as document via bytes", file_name)
        content = await elements_registry.get_element_content(user_id, element_id)
        input_document = BufferedInputFile(content, filename=str(Path(file_name).with_suffix(".png")))
        document_message = await callback.message.answer_document(document=input_document, caption=html.escape(file_name))
        document = document_message.document
        assert document is not None, "document was not sent"
        logger.debug("Get file_id for document %s", file_name)
        await elements_registry.update_element_file_id(user_id, element_id, document.file_id, "document")

    # Force redraw current window since file becomes the last message instead.
    await manager.show(ShowMode.DELETE_AND_SEND)


has_backgrounds_condition = 0 < F["n_backgrounds"]
can_upload_background_condition = cast(MagicFilter, F["n_backgrounds"] < F["limit"])


start_window = Window(
    Case(
        {
            0: Const("У вас нет сохраненных фоновых изображений."),
            ...: Format(
                "Вы сохранили {n_backgrounds} фоновых изображений. Вы можете выбрать фон, нажав на его название."
            ),
        },
        selector="n_backgrounds",
    ),
    Format(
        "Достигнут предел количества сохраненных изображений ({limit}).",
        when=cast(MagicFilter, ~can_upload_background_condition),
    ),
    ScrollingGroup(
        Select(
            Format("🖼️ {item.name}"),
            id="select_background",
            item_id_getter=F.id.resolve,
            items="items",
            when=has_backgrounds_condition,
            on_click=select_image_handler,
        ),
        id="select_background_wrap",
        width=1,
        height=5,
        hide_on_single_page=True,
    ),
    Start(
        Const("Загрузить фон"),
        id="upload_background",
        state=UploadBackgroundStates.START,
        when=can_upload_background_condition,
    ),
    Cancel(Const("❌ Отставеть!")),
    state=BackgroundsStates.START,
    getter=saved_backs_getter,
)


selected_image_window = Window(
    DynamicMedia("background"),
    Format("<b>{escaped_name}</b>"),
    Button(Const("Создать расписание"), id="schedule_from_selected", on_click=not_implemented_button_handler),
    Button(Const("📄️ Прислать без сжатия"), id="send_full", on_click=send_full_handler),
    Button(Const("🚮️ Удалить"), id="delete_selected", on_click=not_implemented_button_handler),
    Button(Const("🌖️ В конец списка"), id="selected_as_old", on_click=not_implemented_button_handler),
    Button(Const("🌒️ В начало списка"), id="selected_as_new", on_click=not_implemented_button_handler),
    SwitchTo(Const("Назад"), id="selected_back", state=BackgroundsStates.START),
    state=BackgroundsStates.SELECTED_IMAGE,
    getter=selected_image_getter,
)


dialog = Dialog(
    start_window,
    selected_image_window,
    name=__file__,
)
