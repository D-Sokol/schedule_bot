import html
import logging
from PIL import UnidentifiedImageError, Image
from typing import Any

from aiogram.filters.state import State, StatesGroup
from aiogram.types import ContentType, Message, CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Cancel, SwitchTo
from magic_filter import F

from bot_registry import RegistryAbstract
from .utils import save_to_dialog_data, active_user_id


logger = logging.getLogger(__file__)


FILE_SIZE_LIMIT = 10 * 1024 * 1024

FILE_SIZE_ERROR_REASON = "file_size"
UNREADABLE_ERROR_REASON = "unreadable"


class UploadBackgroundStates(StatesGroup):
    START = State()
    UPLOADED_NOT_DOCUMENT = State()
    UPLOADED_BAD_DIMENSIONS = State()
    UPLOADED_EXPECT_NAME = State()
    UPLOAD_FAILED = State()


async def on_dialog_start(_: Any, manager: DialogManager):
    registry: RegistryAbstract = manager.middleware_data["registry"]
    user_id = active_user_id(manager)
    template = await registry.get_template(user_id)
    width = template.get("width", 1280)
    manager.dialog_data["expected_width"] = width
    height = template.get("height", 720)
    manager.dialog_data["expected_height"] = height
    logger.debug("Ready to accept image. Expected shape is %d x %d", width, height)


async def handle_image_upload(
        message: Message,
        _: MessageInput,
        manager: DialogManager,
) -> None:
    if (photos := message.photo) is not None:
        logger.debug("Accepted photo object")
        photo = photos[-1]
        file_id = photo.file_id
        file_size = photo.file_size
        sent_name = message.caption
        is_document = False
    elif (document := message.document) is not None:
        logger.debug("Accepted document object")
        file_id = document.file_id
        file_size = document.file_size
        sent_name = None
        is_document = True
    else:
        assert False, "Filters is not properly configured"

    registry: RegistryAbstract = manager.middleware_data["registry"]
    manager.dialog_data["file_size"] = file_size
    manager.dialog_data["file_id"] = file_id
    manager.dialog_data["file_type"] = "document" if is_document else "photo"
    manager.dialog_data["automatic_name"] = sent_name or registry.generate_trivial_name()

    if file_size > FILE_SIZE_LIMIT:
        logger.info("Image rejected: file size is %d", file_size)
        manager.dialog_data["fail_reason"] = FILE_SIZE_ERROR_REASON
        await manager.switch_to(UploadBackgroundStates.UPLOAD_FAILED)
        return

    bot = message.bot
    assert bot is not None, "No bot context in message"
    file = await bot.download(file_id)
    assert file is not None, "image loaded to file system"

    try:
        image = Image.open(file)
    except UnidentifiedImageError:
        logger.info("Image rejected: cannot open as image")
        manager.dialog_data["fail_reason"] = UNREADABLE_ERROR_REASON
        await manager.switch_to(UploadBackgroundStates.UPLOAD_FAILED)
        return

    width, height = image.size
    manager.dialog_data["real_width"] = width
    manager.dialog_data["real_height"] = height
    manager.dialog_data["document"] = image
    manager.dialog_data["resize_mode"] = "ignore"

    if not is_document:
        await manager.switch_to(UploadBackgroundStates.UPLOADED_NOT_DOCUMENT)
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
        logger.debug("Asking about bad image dimensions")
        await manager.switch_to(UploadBackgroundStates.UPLOADED_BAD_DIMENSIONS)
    else:
        logger.debug("Image dimensions OK")
        await manager.switch_to(UploadBackgroundStates.UPLOADED_EXPECT_NAME)


async def save_image(
        update: CallbackQuery | Message,
        _widget: Any,
        manager: DialogManager,
        data: str,
):
    registry: RegistryAbstract = manager.middleware_data["registry"]
    image: Image.Image = manager.dialog_data["document"]
    expected = (manager.dialog_data["expected_width"], manager.dialog_data["expected_height"])
    resize_mode = manager.dialog_data["resize_mode"]
    file_id = manager.dialog_data["file_id"]
    file_type = manager.dialog_data["file_type"]
    user_id = active_user_id(manager)
    logger.info("Saving new image: %s", data)
    new_element = await registry.save_element(
        image, user_id,
        element_name=data,
        file_id_document=file_id if file_type == "document" else None,
        file_id_photo=file_id if file_type == "photo" else None,
        target_size=expected,
        resize_mode=resize_mode,
    )

    if isinstance(update, CallbackQuery):
        message = update.message
    else:
        message = update
    await message.answer(f"Фон сохранен!\n<b>{html.escape(data)}</b>")
    # Since we send a custom message, dialogs should send new one to use the latest message in the chat
    await manager.done(result={"element": new_element}, show_mode=ShowMode.SEND)


async def save_image_auto_name(
        update: CallbackQuery,
        _widget: Any,
        manager: DialogManager,
):
    auto_name = manager.dialog_data["automatic_name"]
    logger.debug("Confirmed automatic name: %s", auto_name)
    return await save_image(update, _widget, manager, data=auto_name)


upload_image_window = Window(
    Const("Загрузите изображение для использования в качестве фона."),
    Const("Советую отправить картинку как файл, чтобы избежать потери качества!"),
    Cancel(Const("❌ Отставеть!"), id="cancel_upload"),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=UploadBackgroundStates.START,
)

uploaded_not_document_window = Window(
    Const(
        "Вы отправили картинку не как файл. Это может привести к потере качества. Можете загрузить картинку еще раз?"
    ),
    Button(Const("И так сойдет"), id="confirm_non_document_upload", on_click=check_dimensions),
    Cancel(Const("❌ Отставеть!"), id="cancel_upload_nodoc"),
    MessageInput(handle_image_upload, content_types=[ContentType.DOCUMENT]),
    state=UploadBackgroundStates.UPLOADED_NOT_DOCUMENT,
)

uploaded_bad_dimensions_window = Window(
    Format(
        "Размер загруженного изображения ({dialog_data[real_width]}x{dialog_data[real_height]}) "
        "отличается от ожидаемого ({dialog_data[expected_width]}x{dialog_data[expected_height]})"
    ),
    Const("Вы можете загрузить другую картинку или все равно использовать эту."),
    SwitchTo(
        Const("Растянуть до нужного размера"),
        id="bad_dimensions_resize",
        state=UploadBackgroundStates.UPLOADED_EXPECT_NAME,
        on_click=save_to_dialog_data("resize_mode", "resize"),
    ),
    SwitchTo(
        Const("Обрезать картинку"),
        id="bad_dimensions_crop",
        state=UploadBackgroundStates.UPLOADED_EXPECT_NAME,
        on_click=save_to_dialog_data("resize_mode", "crop")
    ),
    SwitchTo(Const("И так сойдет"), id="bad_dimensions_ignore", state=UploadBackgroundStates.UPLOADED_EXPECT_NAME),
    Cancel(Const("❌ Отставеть!"), id="cancel_upload_dim"),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=UploadBackgroundStates.UPLOADED_BAD_DIMENSIONS,
)

uploaded_expect_name_window = Window(
    Const("Введите имя для этой картинки, чтобы потом узнать ее в списке!"),
    Format("По умолчанию картинка будет называться {dialog_data[automatic_name]}."),
    TextInput(id="background_name_input", on_success=save_image),
    Button(Const("И так сойдет"), id="confirm_autogenerated_name", on_click=save_image_auto_name),
    Cancel(Const("❌ Отставеть!"), id="cancel_upload_name"),
    state=UploadBackgroundStates.UPLOADED_EXPECT_NAME,
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
    Cancel(Const("Смириться"), id="accept_failed_upload"),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=UploadBackgroundStates.UPLOAD_FAILED,
)


dialog = Dialog(
    upload_image_window,
    uploaded_not_document_window,
    uploaded_bad_dimensions_window,
    uploaded_expect_name_window,
    upload_failed_window,
    on_start=on_dialog_start,
    name=__file__,
)
