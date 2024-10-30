import html
import logging
from PIL import UnidentifiedImageError, Image
from datetime import datetime
from typing import Any, Awaitable, Callable, cast

from aiogram.filters.state import State, StatesGroup
from aiogram.types import ContentType, Message, CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager, Data
from aiogram_dialog.api.entities import MediaAttachment, MediaId, ShowMode
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.text import Const, Format, Case
from aiogram_dialog.widgets.kbd import Button, Cancel, Select, SwitchTo, ScrollingGroup
from aiogram_dialog.widgets.media import DynamicMedia
from magic_filter import F, MagicFilter

from elements_registry import ElementsRegistryAbstract


logger = logging.getLogger(__file__)


BACKGROUNDS_LIMIT = 6
FILE_SIZE_LIMIT = 10 * 1024 * 1024

FILE_SIZE_ERROR_REASON = "file_size"
UNREADABLE_ERROR_REASON = "unreadable"


class BackgroundsStates(StatesGroup):
    START = State()
    UPLOAD_IMAGE = State()
    UPLOADED_NOT_DOCUMENT = State()
    UPLOADED_BAD_DIMENSIONS = State()
    UPLOADED_EXPECT_NAME = State()
    UPLOAD_FAILED = State()
    SELECTED_IMAGE = State()


async def not_implemented_button_handler(callback: CallbackQuery, _button: Button, _manager: DialogManager):
    await callback.answer("Функционал не реализован.")


async def on_dialog_start(_: Any, manager: DialogManager):
    elements_registry: ElementsRegistryAbstract = manager.middleware_data["elements_registry"]
    template = await elements_registry.get_template(None)  # TODO: user_id
    manager.dialog_data["expected_width"] = template.get("width", 1280)
    manager.dialog_data["expected_height"] = template.get("height", 720)


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
    file_id: str = dialog_manager.dialog_data["file_id"]
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
    manager.dialog_data["file_id"] = element["file_id"]
    manager.dialog_data["file_name"] = element["name"]
    await manager.switch_to(BackgroundsStates.SELECTED_IMAGE)


async def send_full_handler(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    file_id: str = manager.dialog_data["file_id"]
    file_name: str = manager.dialog_data["file_name"]
    # FIXME: this causes TelegramBadRequest if img was accepted as photo.
    await callback.message.answer_document(document=file_id, caption=html.escape(file_name))
    # Force redraw current window since file becomes the last message instead.
    await manager.show(ShowMode.DELETE_AND_SEND)


def save_to_dialog_data(key: str, value: Data) -> Callable[[CallbackQuery, Button, DialogManager], Awaitable]:
    async def callback(_update: CallbackQuery, _widget: Button, manager: DialogManager) -> None:
        manager.dialog_data[key] = value
    return callback


async def handle_image_upload(
        message: Message,
        _: MessageInput,
        manager: DialogManager,
) -> None:
    if (photos := message.photo) is not None:
        photo = photos[-1]
        file_id = photo.file_id
        file_size = photo.file_size
        is_document = False
    elif (document := message.document) is not None:
        file_id = document.file_id
        file_size = document.file_size
        is_document = True
    else:
        assert False, "Filters is not properly configured"

    now = datetime.now()
    manager.dialog_data["file_size"] = file_size
    manager.dialog_data["file_id"] = file_id
    manager.dialog_data["automatic_name"] = f"Фон {now.isoformat(sep=' ', timespec='seconds')}"

    if file_size > FILE_SIZE_LIMIT:
        manager.dialog_data["fail_reason"] = FILE_SIZE_ERROR_REASON
        await manager.switch_to(BackgroundsStates.UPLOAD_FAILED)
        return

    bot = message.bot
    assert bot is not None, "No bot context in message"
    file = await bot.download(file_id)
    assert file is not None, "image loaded to file system"

    try:
        image = Image.open(file)
    except UnidentifiedImageError:
        manager.dialog_data["fail_reason"] = UNREADABLE_ERROR_REASON
        await manager.switch_to(BackgroundsStates.UPLOAD_FAILED)
        return

    width, height = image.size
    manager.dialog_data["real_width"] = width
    manager.dialog_data["real_height"] = height
    manager.dialog_data["document"] = image
    manager.dialog_data["resize_mode"] = "ignore"

    if not is_document:
        await manager.switch_to(BackgroundsStates.UPLOADED_NOT_DOCUMENT)
    else:
        await check_dimensions(message, _, manager)


async def check_dimensions(
        _update: Any,
        _widget: Any,
        manager: DialogManager
) -> None:
    real = (manager.dialog_data["real_width"], manager.dialog_data["real_height"])
    expected = (manager.dialog_data["expected_width"], manager.dialog_data["expected_height"])
    if real != expected:
        await manager.switch_to(BackgroundsStates.UPLOADED_BAD_DIMENSIONS)
    else:
        await manager.switch_to(BackgroundsStates.UPLOADED_EXPECT_NAME)


async def save_image(
        update: CallbackQuery | Message,
        _widget: Any,
        manager: DialogManager,
        data: str,
):
    elements_registry: ElementsRegistryAbstract = manager.middleware_data["elements_registry"]
    image: Image.Image = manager.dialog_data["document"]
    expected = (manager.dialog_data["expected_width"], manager.dialog_data["expected_height"])
    resize_mode = manager.dialog_data["resize_mode"]
    file_id = manager.dialog_data["file_id"]
    await elements_registry.save_element(
        image, None,  # TODO: user_id
        element_name=data,
        file_id=file_id,
        target_size=expected,
        resize_mode=resize_mode,
    )

    if isinstance(update, CallbackQuery):
        message = update.message
    else:
        message = update
    await message.answer(f"Фон сохранен!\n<b>{html.escape(data)}</b>")
    # Since we send a custom message, dialogs should send new one to use the latest message in the chat
    await manager.switch_to(BackgroundsStates.START, show_mode=ShowMode.SEND)


async def save_image_auto_name(
        update: CallbackQuery,
        _widget: Any,
        manager: DialogManager,
):
    auto_name = manager.dialog_data["automatic_name"]
    return await save_image(update, _widget, manager, data=auto_name)


has_backgrounds_condition = 0 < F["n_backgrounds"]
can_upload_background_condition = cast(MagicFilter, F["n_backgrounds"] < F["limit"])


start_window = Window(
    Case(
        {
            0: Const("У вас нет сохраненных фоновых изображений."),
            ...: Format("Вы сохранили {n_backgrounds} фоновых изображений. Вы можете выбрать фон, нажав на его название."),
        },
        selector="n_backgrounds",
    ),
    Format(
        "Достигнут предел количества сохраненных изображений ({limit}).",
        when=cast(MagicFilter, ~can_upload_background_condition),
    ),
    ScrollingGroup(
        Select(
            Format("🖼️ {item[name]}"),
            id="select_background",
            item_id_getter=F["id"].resolve,
            items="items",
            when=has_backgrounds_condition,
            on_click=select_image_handler,
        ),
        id="select_background_wrap",
        width=1,
        height=5,
        hide_on_single_page=True,
    ),
    SwitchTo(Const("Загрузить фон"), id="upload_background", state=BackgroundsStates.UPLOAD_IMAGE, when=can_upload_background_condition),
    Cancel(Const("❌ Отставеть!")),
    state=BackgroundsStates.START,
    getter=saved_backs_getter,
)

upload_image_window = Window(
    Const("Загрузите изображение для использования в качестве фона."),
    Const("Советую отправить картинку как файл, чтобы избежать потери качества!"),
    SwitchTo(Const("❌ Отставеть!"), id="cancel_upload", state=BackgroundsStates.START),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=BackgroundsStates.UPLOAD_IMAGE,
)

uploaded_not_document_window = Window(
    Const("Вы отправили картинку не как файл. Это может привести к потере качества. Можете загрузить картинку еще раз?"),
    Button(Const("И так сойдет"), id="confirm_non_document_upload", on_click=check_dimensions),
    SwitchTo(Const("❌ Отставеть!"), id="cancel_upload_nodoc", state=BackgroundsStates.START),
    MessageInput(handle_image_upload, content_types=[ContentType.DOCUMENT]),
    state=BackgroundsStates.UPLOADED_NOT_DOCUMENT,
)

uploaded_bad_dimensions_window = Window(
    Format(
        "Размер загруженного изображения ({dialog_data[real_width]}x{dialog_data[real_height]}) "
        "отличается от ожидаемого ({dialog_data[expected_width]}x{dialog_data[expected_height]})"
    ),
    Const("Вы можете загрузить другую картинку или все равно использовать эту."),
    SwitchTo(
        Const("Растянуть до нужного размера"), id="bad_dimensions_resize", state=BackgroundsStates.UPLOADED_EXPECT_NAME,
        on_click=save_to_dialog_data("resize_mode", "resize")
    ),
    SwitchTo(
        Const("Обрезать картинку"), id="bad_dimensions_crop", state=BackgroundsStates.UPLOADED_EXPECT_NAME,
        on_click=save_to_dialog_data("resize_mode", "crop")
    ),
    SwitchTo(Const("И так сойдет"), id="bad_dimensions_ignore", state=BackgroundsStates.UPLOADED_EXPECT_NAME),
    SwitchTo(Const("❌ Отставеть!"), id="cancel_upload_dim", state=BackgroundsStates.START),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=BackgroundsStates.UPLOADED_BAD_DIMENSIONS,
)

uploaded_expect_name_window = Window(
    Const("Введите имя для этой картинки, чтобы потом узнать ее в списке!"),
    Format("По умолчанию картинка будет называться {dialog_data[automatic_name]}."),
    TextInput(id="background_name_input", on_success=save_image),
    Button(Const("И так сойдет"), id="confirm_autogenerated_name", on_click=save_image_auto_name),
    SwitchTo(Const("❌ Отставеть!"), id="cancel_upload_name", state=BackgroundsStates.START),
    state=BackgroundsStates.UPLOADED_EXPECT_NAME,
)

upload_failed_window = Window(
    Const(
        "Размер этого файла слишком большой. Возможно, это и не картинка вовсе.",
        when=FILE_SIZE_ERROR_REASON == F["dialog_data"]["fail_reason"],
    ),
    Const(
        "Не удалось открыть присланный файл как изображение.",
        when=UNREADABLE_ERROR_REASON == F["dialog_data"]["fail_reason"],
    ),
    Const("Фон не может быть сохранен."),
    SwitchTo(Const("Смириться"), id="accept_failed_upload", state=BackgroundsStates.START),
    state=BackgroundsStates.UPLOAD_FAILED,
)

selected_image_window = Window(
    # FIXME: this works only if image was loaded as photo, not document.
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
    upload_image_window,
    uploaded_not_document_window,
    uploaded_bad_dimensions_window,
    uploaded_expect_name_window,
    upload_failed_window,
    selected_image_window,
    on_start=on_dialog_start,
    name=__file__,
)
