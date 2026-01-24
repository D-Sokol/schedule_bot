import html
import logging
from pathlib import Path
from typing import Any, cast

from aiogram.types import BufferedInputFile, CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.api.entities import MediaAttachment, MediaId, ShowMode
from aiogram_dialog.widgets.common import ManagedScroll
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Column,
    CurrentPage,
    FirstPage,
    LastPage,
    NextPage,
    PrevPage,
    Row,
    Select,
    StubScroll,
    SwitchTo,
)
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Const, Format
from fluentogram import TranslatorRunner
from magic_filter import F, MagicFilter

from app.middlewares.i18n import I18N_KEY
from app.middlewares.registry import ELEMENT_REGISTRY_KEY
from bot_registry import ElementsRegistryAbstract

from .custom_widgets import FluentFormat, StartWithData
from .states import BackgroundsStates, ScheduleStates, UploadBackgroundStates
from .utils import active_user_id, current_user_id, has_admin_privileges

logger = logging.getLogger(__name__)

BACKGROUNDS_PAGE_SIZE = 5

ID_BACKGROUND_PAGER = "background_pager"
DIALOG_ELEMENT_ID_KEY = "element_id"
DIALOG_BACKGROUND_ITEMS_KEY = "items"
DIALOG_N_BACKGROUNDS_KEY = "n_backgrounds"
DIALOG_N_PAGES_KEY = "n_pages"
DIALOG_LIMIT_KEY = "limit"
DIALOG_BACKGROUND_KEY = "background"
DIALOG_ESCAPED_NAME_KEY = "escaped_name"
DIALOG_IS_ELEMENT_READY_KEY = "ready"
DIALOG_ELEMENT_NAME_KEY = "element_name"
START_DATA_SELECT_ONLY_KEY = "select_only"
START_DATA_GLOBAL_SCOPE_KEY = "global_scope"


def _count_n_pages(n_items: int, page_size: int) -> int:
    if n_items < 0 or page_size < 1:
        raise ValueError(f"Cannot compute page size for {n_items=} and {page_size=}")
    full_pages, rest = divmod(n_items, page_size)
    return full_pages + (1 if rest else 0)


async def backgrounds_limit_getter(
    dialog_manager: DialogManager,
    element_registry: ElementsRegistryAbstract,
    **_,
):
    user_id = active_user_id(dialog_manager)
    backgrounds_limit = await element_registry.get_elements_limit(user_id)
    logger.debug("Limit for user %d is %d backgrounds", user_id, backgrounds_limit)
    return {
        DIALOG_LIMIT_KEY: backgrounds_limit,
    }


async def backgrounds_pageinfo_getter(
    dialog_manager: DialogManager,
    element_registry: ElementsRegistryAbstract,
    **_,
):
    user_id = active_user_id(dialog_manager)
    n_elements = await element_registry.get_elements_count(user_id)
    logger.debug("User %d has %d backgrounds loaded", user_id, n_elements)
    return {
        DIALOG_N_BACKGROUNDS_KEY: n_elements,
        DIALOG_N_PAGES_KEY: _count_n_pages(n_elements, page_size=BACKGROUNDS_PAGE_SIZE),
    }


async def backgrounds_page_getter(
    dialog_manager: DialogManager,
    element_registry: ElementsRegistryAbstract,
    **_,
):
    pageinfo_data = await backgrounds_pageinfo_getter(dialog_manager, element_registry)
    n_pages = pageinfo_data[DIALOG_N_PAGES_KEY]
    if n_pages == 0:
        logger.debug("Early return for page getter, since there are no backgrounds")
        return {
            DIALOG_BACKGROUND_ITEMS_KEY: [],
            **pageinfo_data,
        }

    user_id = active_user_id(dialog_manager)
    scroll = cast(ManagedScroll, dialog_manager.find(ID_BACKGROUND_PAGER))
    current_page = await scroll.get_page()
    if current_page >= n_pages:
        # Requested page without a data, which possible after background deletion
        logger.debug(
            "Update current page from %d to %d for user %d, no data on requested one",
            current_page,
            n_pages - 1,
            user_id,
        )
        current_page = n_pages - 1
        assert current_page >= 0, "Incorrect page management"
        await scroll.set_page(current_page)

    logger.debug("Loading backgrounds for user %d, page %d/%d", user_id, current_page + 1, n_pages)
    elements = await element_registry.get_elements(user_id)
    elements = elements[BACKGROUNDS_PAGE_SIZE * current_page :][:BACKGROUNDS_PAGE_SIZE]  # TODO: nest into the query
    return {
        DIALOG_BACKGROUND_ITEMS_KEY: elements,
        **pageinfo_data,
    }


async def selected_image_getter(
    dialog_manager: DialogManager, element_registry: ElementsRegistryAbstract, **_
) -> dict[str, Any]:
    element_id: str = dialog_manager.dialog_data[DIALOG_ELEMENT_ID_KEY]
    user_id = active_user_id(dialog_manager)
    element = await element_registry.get_element(user_id, element_id)
    file_id: str = element.file_id_photo

    if file_id is None:
        file_id = element_registry.format_bot_uri(user_id, element_id)
    return {
        DIALOG_BACKGROUND_KEY: MediaAttachment(ContentType.PHOTO, file_id=MediaId(file_id)),
        DIALOG_ESCAPED_NAME_KEY: html.escape(element.name),
        DIALOG_IS_ELEMENT_READY_KEY: await element_registry.is_element_content_ready(user_id, element_id),
    }


async def selected_image_name_getter(
    dialog_manager: DialogManager, element_registry: ElementsRegistryAbstract, **_
) -> dict[str, str]:
    element_id: str = dialog_manager.dialog_data[DIALOG_ELEMENT_ID_KEY]
    user_id = active_user_id(dialog_manager)
    element = await element_registry.get_element(user_id, element_id)
    return {
        DIALOG_ELEMENT_NAME_KEY: element.name,
    }


async def select_image_handler(
    _callback: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
    item_id: str,
):
    user_id = active_user_id(manager)
    manager.dialog_data[DIALOG_ELEMENT_ID_KEY] = item_id
    logger.debug("Getter: selected image %s/%s", user_id, item_id)
    if cast(dict[str, Any], manager.start_data)[START_DATA_SELECT_ONLY_KEY]:
        logging.debug("Finishing dialog since select only mode requested")
        await manager.done(result={DIALOG_ELEMENT_ID_KEY: item_id})
    else:
        await manager.switch_to(BackgroundsStates.SELECTED_IMAGE)


async def delete_image_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    element_id: str = manager.dialog_data[DIALOG_ELEMENT_ID_KEY]
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    user_id = active_user_id(manager)
    element = await registry.get_element(user_id, element_id)

    if user_id is None and not has_admin_privileges(manager):
        logger.info("Removing global element is blocked for user %d", current_user_id(manager))
        await callback.answer(i18n.get("notify-forbidden"))
        return
    await registry.delete_element(user_id, element_id)
    await callback.answer(i18n.get("notify-remove_image", escaped_name=html.escape(element.name)))


async def send_full_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    user_id = active_user_id(manager)
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    element_id: str = manager.dialog_data[DIALOG_ELEMENT_ID_KEY]
    element = await registry.get_element(user_id, element_id)
    file_name: str = element.name
    file_id: str | None = element.file_id_document
    if file_id is not None:
        logger.debug("Sending full version for image %s", file_name)
        await callback.message.answer_document(document=file_id, caption=html.escape(file_name))
    else:
        logger.info("Sending image %s as document via bytes", file_name)
        # We don't check existing via `.is_element_content_ready` since this is not called unless so.
        content = await registry.get_element_content(user_id, element_id)
        input_document = BufferedInputFile(content, filename=str(Path(file_name).with_suffix(".png")))
        document_message = await callback.message.answer_document(
            document=input_document, caption=html.escape(file_name)
        )
        document = document_message.document
        assert document is not None, "document was not sent"
        logger.debug("Get file_id for document %s", file_name)
        await registry.update_element_file_id(user_id, element.element_id, document.file_id, "document")

    # Force redraw current window since file becomes the last message instead.
    # Setting show_mode property of manager is the correct way to do so and works only for one action.
    manager.show_mode = ShowMode.DELETE_AND_SEND


async def make_new_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    user_id = active_user_id(manager)
    element_id: str = manager.dialog_data[DIALOG_ELEMENT_ID_KEY]
    element = await registry.get_element(user_id, element_id)

    if user_id is None and not has_admin_privileges(manager):
        logger.info("Reordering global elements is blocked for user %d", current_user_id(manager))
        await callback.answer(i18n.get("notify-forbidden"))
        return
    await registry.reorder_make_first(user_id, element_id)
    await manager.switch_to(BackgroundsStates.START)

    await callback.answer(i18n.get("notify-reorder.first", name=html.escape(element.name)))


async def make_old_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    user_id = active_user_id(manager)
    element_id: str = manager.dialog_data[DIALOG_ELEMENT_ID_KEY]
    element = await registry.get_element(user_id, element_id)

    if user_id is None and not has_admin_privileges(manager):
        logger.info("Reordering global elements is blocked for user %d", current_user_id(manager))
        await callback.answer(i18n.get("notify-forbidden"))
        return
    await registry.reorder_make_last(user_id, element_id)
    await manager.switch_to(BackgroundsStates.START)

    await callback.answer(i18n.get("notify-reorder.last", name=html.escape(element.name)))


async def rename_image(
    message: Message,
    _widget: Any,
    manager: DialogManager,
    data: str,
):
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    user_id = active_user_id(manager)
    element_id: str = manager.dialog_data[DIALOG_ELEMENT_ID_KEY]

    if user_id is None and not has_admin_privileges(manager):
        logger.info("Renaming global element is blocked for user %d", current_user_id(manager))
        i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
        await message.answer(i18n.get("notify-forbidden"))
        return
    await registry.update_element_name(user_id, element_id, name=data)
    await manager.switch_to(BackgroundsStates.SELECTED_IMAGE)


has_backgrounds_condition = 0 < F[DIALOG_N_BACKGROUNDS_KEY]
can_upload_background_condition = cast(MagicFilter, F[DIALOG_N_BACKGROUNDS_KEY] < F[DIALOG_LIMIT_KEY])


start_window = Window(
    FluentFormat("dialog-backgrounds-main.number", n_backgrounds=F[DIALOG_N_BACKGROUNDS_KEY]),
    FluentFormat(
        "dialog-backgrounds-main.limit",
        when=cast(MagicFilter, ~can_upload_background_condition),
        limit=F[DIALOG_LIMIT_KEY],
    ),
    Column(
        Select(
            FluentFormat("dialog-backgrounds-main.item", item_name=F["item"].name),
            id="select_background",
            item_id_getter=F.element_id.cast(str).resolve,
            items=DIALOG_BACKGROUND_ITEMS_KEY,
            when=has_backgrounds_condition,
            on_click=select_image_handler,
        ),
    ),
    StubScroll(
        id=ID_BACKGROUND_PAGER,
        pages=DIALOG_N_PAGES_KEY,
    ),
    Row(
        FirstPage(
            scroll=ID_BACKGROUND_PAGER,
            text=Format("⏮️ {target_page1}"),
        ),
        PrevPage(
            scroll=ID_BACKGROUND_PAGER,
            text=Const("◀️"),
        ),
        CurrentPage(
            scroll=ID_BACKGROUND_PAGER,
            text=Format("{current_page1}"),
        ),
        NextPage(
            scroll=ID_BACKGROUND_PAGER,
            text=Const("▶️"),
        ),
        LastPage(
            scroll=ID_BACKGROUND_PAGER,
            text=Format("{target_page1} ⏭️"),
        ),
        when=F[DIALOG_N_PAGES_KEY] > 1,
    ),
    StartWithData(
        FluentFormat("dialog-backgrounds-main.upload"),
        id="upload_background",
        state=UploadBackgroundStates.START,
        when=can_upload_background_condition & ~F["start_data"][START_DATA_SELECT_ONLY_KEY],
        data_keys=[START_DATA_GLOBAL_SCOPE_KEY],
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=BackgroundsStates.START,
    getter=[backgrounds_limit_getter, backgrounds_page_getter],
)


selected_image_window = Window(
    DynamicMedia(selector=DIALOG_BACKGROUND_KEY, when=DIALOG_IS_ELEMENT_READY_KEY),
    FluentFormat("dialog-backgrounds-selected.not_ready", when=~F[DIALOG_IS_ELEMENT_READY_KEY]),
    FluentFormat("dialog-backgrounds-selected"),
    StartWithData(
        FluentFormat("dialog-backgrounds-selected.create"),
        id="schedule_from_selected",
        state=ScheduleStates.EXPECT_TEXT,
        dialog_data_keys=[DIALOG_ELEMENT_ID_KEY],
    ),
    SwitchTo(FluentFormat("dialog-backgrounds-selected.rename"), id="rename_selected", state=BackgroundsStates.RENAME),
    Button(
        FluentFormat("dialog-backgrounds-selected.full"),
        id="send_full",
        on_click=send_full_handler,
        when=DIALOG_IS_ELEMENT_READY_KEY,
    ),
    SwitchTo(
        FluentFormat("dialog-backgrounds-selected.delete"), id="delete_selected", state=BackgroundsStates.CONFIRM_DELETE
    ),
    Button(FluentFormat("dialog-backgrounds-selected.old"), id="selected_as_old", on_click=make_old_handler),
    Button(FluentFormat("dialog-backgrounds-selected.new"), id="selected_as_new", on_click=make_new_handler),
    SwitchTo(FluentFormat("dialog-cancel"), id="selected_back", state=BackgroundsStates.START),
    state=BackgroundsStates.SELECTED_IMAGE,
    getter=selected_image_getter,
)

rename_image_window = Window(
    FluentFormat("dialog-backgrounds-rename"),
    SwitchTo(
        FluentFormat("dialog-backgrounds-rename.cancel"), id="cancel_rename", state=BackgroundsStates.SELECTED_IMAGE
    ),
    TextInput(id="rename", type_factory=ElementsRegistryAbstract.validate_name, on_success=rename_image),
    state=BackgroundsStates.RENAME,
)

confirm_delete_window = Window(
    FluentFormat(
        "dialog-backgrounds-delete",
        escaped_name=F[DIALOG_ELEMENT_NAME_KEY].func(html.escape),
    ),
    SwitchTo(
        FluentFormat("dialog-backgrounds-delete.confirm"),
        id="confirm_delete",
        state=BackgroundsStates.START,
        on_click=delete_image_handler,
    ),
    SwitchTo(
        FluentFormat("dialog-backgrounds-delete.cancel"), id="cancel_delete", state=BackgroundsStates.SELECTED_IMAGE
    ),
    state=BackgroundsStates.CONFIRM_DELETE,
    getter=selected_image_name_getter,
)


dialog = Dialog(
    start_window,
    selected_image_window,
    confirm_delete_window,
    rename_image_window,
    name=__name__,
)
