import html
import logging
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from aiogram.types import ContentType, CallbackQuery, BufferedInputFile

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId, ShowMode
from aiogram_dialog.widgets.kbd import Button, Cancel, Select, SwitchTo, ScrollingGroup
from aiogram_dialog.widgets.media import DynamicMedia
from magic_filter import F, MagicFilter

from bot_registry import ElementsRegistryAbstract
from database_models import ImageAsset
from .states import BackgroundsStates, UploadBackgroundStates, ScheduleStates
from .utils import not_implemented_button_handler, active_user_id, StartWithData, FluentFormat


logger = logging.getLogger(__file__)


async def saved_backs_getter(
        dialog_manager: DialogManager, element_registry: ElementsRegistryAbstract, _only_count: bool = False, **_,
) -> dict[str, Any]:
    user_id = active_user_id(dialog_manager)
    if _only_count:
        items = []
        n_items = await element_registry.get_elements_count(user_id)
    else:
        items = await element_registry.get_elements(user_id)
        n_items = len(items)
    backgrounds_limit = await element_registry.get_elements_limit(user_id)
    logger.debug("Getter: %d images found with limit %d", len(items), backgrounds_limit)
    return {
        "items": items,
        "n_backgrounds": n_items,
        "limit": backgrounds_limit,
    }


async def selected_image_getter(dialog_manager: DialogManager, **_) -> dict[str, Any]:
    file_name: str = dialog_manager.dialog_data["element"].name
    file_id: str = dialog_manager.dialog_data["element"].file_id_photo
    user_id = active_user_id(dialog_manager)
    if file_id is None:
        element_id: UUID = dialog_manager.dialog_data["element"].element_id
        file_id = f"bot://{user_id or 0}/{element_id}"
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
    registry: ElementsRegistryAbstract = manager.middleware_data["element_registry"]
    user_id = active_user_id(manager)
    element = await registry.get_element(user_id, item_id)
    manager.dialog_data["element"] = element
    logger.debug("Getter: selected image %s/%s, id %s", user_id, element.name, item_id)
    if manager.start_data["select_only"]:
        logging.debug("Finishing dialog since select only mode requested")
        await manager.done(result={"element": element})
    else:
        await manager.switch_to(BackgroundsStates.SELECTED_IMAGE)


async def send_full_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    element: ImageAsset = manager.dialog_data["element"]
    file_name: str = element.name
    file_id: str = element.file_id_document
    if file_id is not None:
        logger.debug("Sending full version for image %s", file_name)
        await callback.message.answer_document(document=file_id, caption=html.escape(file_name))
    else:
        user_id = active_user_id(manager)
        registry: ElementsRegistryAbstract = manager.middleware_data["element_registry"]
        logger.info("Sending image %s as document via bytes", file_name)
        content = await registry.get_element_content(user_id, element.element_id)
        input_document = BufferedInputFile(content, filename=str(Path(file_name).with_suffix(".png")))
        document_message = await callback.message.answer_document(document=input_document, caption=html.escape(file_name))
        document = document_message.document
        assert document is not None, "document was not sent"
        logger.debug("Get file_id for document %s", file_name)
        await registry.update_element_file_id(user_id, element.element_id, document.file_id, "document")

    # Force redraw current window since file becomes the last message instead.
    # Setting show_mode property of manager is the correct way to do so and works only for one action.
    manager.show_mode = ShowMode.DELETE_AND_SEND


has_backgrounds_condition = 0 < F["n_backgrounds"]
can_upload_background_condition = cast(MagicFilter, F["n_backgrounds"] < F["limit"])


start_window = Window(
    FluentFormat("dialog-backgrounds-main.number", n_backgrounds=F["n_backgrounds"]),
    FluentFormat(
        "dialog-backgrounds-main.limit",
        when=cast(MagicFilter, ~can_upload_background_condition),
        limit=F["limit"],
    ),
    ScrollingGroup(
        Select(
            FluentFormat("dialog-backgrounds-main.item", item_name=F["item"].name),
            id="select_background",
            item_id_getter=F.element_id.cast(str).resolve,
            items="items",
            when=has_backgrounds_condition,
            on_click=select_image_handler,
        ),
        id="select_background_wrap",
        width=1,
        height=5,
        hide_on_single_page=True,
    ),
    StartWithData(
        FluentFormat("dialog-backgrounds-main.upload"),
        id="upload_background",
        state=UploadBackgroundStates.START,
        when=can_upload_background_condition & ~F["start_data"]["select_only"],
        data_keys=["global_scope"],
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=BackgroundsStates.START,
    getter=saved_backs_getter,
)


selected_image_window = Window(
    DynamicMedia("background"),
    FluentFormat("dialog-backgrounds-selected"),
    StartWithData(
        FluentFormat("dialog-backgrounds-selected.create"),
        id="schedule_from_selected",
        state=ScheduleStates.EXPECT_TEXT,
        dialog_data_keys=["element"],
    ),
    Button(FluentFormat("dialog-backgrounds-selected.rename"), id="rename_selected", on_click=not_implemented_button_handler),
    Button(FluentFormat("dialog-backgrounds-selected.full"), id="send_full", on_click=send_full_handler),
    Button(FluentFormat("dialog-backgrounds-selected.delete"), id="delete_selected", on_click=not_implemented_button_handler),
    Button(FluentFormat("dialog-backgrounds-selected.old"), id="selected_as_old", on_click=not_implemented_button_handler),
    Button(FluentFormat("dialog-backgrounds-selected.new"), id="selected_as_new", on_click=not_implemented_button_handler),
    SwitchTo(FluentFormat("dialog-cancel"), id="selected_back", state=BackgroundsStates.START),
    state=BackgroundsStates.SELECTED_IMAGE,
    getter=selected_image_getter,
)


dialog = Dialog(
    start_window,
    selected_image_window,
    name=__file__,
)
