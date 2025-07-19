import html
import logging
from enum import StrEnum
from typing import Any, cast

from aiogram.types import ContentType, Message, CallbackQuery

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, SwitchTo
from fluentogram import TranslatorRunner
from magic_filter import F
from PIL import UnidentifiedImageError, Image

from app.middlewares.db_session import USER_ENTITY_KEY
from app.middlewares.i18n import I18N_KEY
from app.middlewares.registry import ELEMENT_REGISTRY_KEY, TEMPLATE_REGISTRY_KEY
from bot_registry import ElementsRegistryAbstract, TemplateRegistryAbstract
from core.entities import UserEntity
from core.exceptions import DuplicateNameException
from .custom_widgets import FluentFormat
from .states import UploadBackgroundStates
from .utils import save_to_dialog_data, active_user_id, has_admin_privileges

logger = logging.getLogger(__name__)

FILE_SIZE_LIMIT = 10 * 1024 * 1024


class _ErrorReason(StrEnum):
    UNREADABLE = "unreadable"
    FILE_SIZE = "file_size"


class _FileType(StrEnum):
    DOCUMENT = "document"
    PHOTO = "photo"


DIALOG_FILE_ID_KEY = "file_id"
DIALOG_FILE_TYPE_KEY = "file_type"
DIALOG_FILE_SIZE_KEY = "file_size"
DIALOG_AUTOMATIC_NAME_KEY = "automatic_name"
DIALOG_FAIL_REASON_KEY = "fail_reason"
DIALOG_REAL_WIDTH_KEY = "real_width"
DIALOG_REAL_HEIGHT_KEY = "real_height"
DIALOG_RESIZE_MODE_KEY = "resize_mode"
DIALOG_EXPECTED_WIDTH_KEY = "expected_width"
DIALOG_EXPECTED_HEIGHT_KEY = "expected_height"
START_DATA_GLOBAL_SCOPE_KEY = "global_scope"
RESULT_ELEMENT_ID_KEY = "element_id"


async def on_dialog_start(_: Any, manager: DialogManager):
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    template_registry: TemplateRegistryAbstract = manager.middleware_data[TEMPLATE_REGISTRY_KEY]
    user_id = active_user_id(manager)
    limit = await registry.get_elements_limit(user_id)
    current = await registry.get_elements_count(user_id)
    if current >= limit:
        # This log message is ERROR-level because in this case corresponding buttons should be hidden.
        logger.error("Uploading images for %s is blocked since limit %d is reached!", user_id, limit)
        await manager.done()
        return

    template = (await template_registry.get_template(user_id)) or (await template_registry.get_template(None))
    if template is not None:
        width = template.width
        height = template.height
    else:
        logging.warning("No template for %d and global is missing, skip checking dimensions!", user_id)
        width = height = None
    manager.dialog_data[DIALOG_EXPECTED_WIDTH_KEY] = width
    manager.dialog_data[DIALOG_EXPECTED_HEIGHT_KEY] = height
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
        file_size = cast(int, photo.file_size)
        sent_name = message.caption
        is_document = False
    elif (document := message.document) is not None:
        logger.debug("Accepted document object")
        file_id = document.file_id
        file_size = cast(int, document.file_size)
        sent_name = message.caption or document.file_name or None
        is_document = True
    else:
        assert False, "Filters is not properly configured"

    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    manager.dialog_data[DIALOG_FILE_SIZE_KEY] = file_size
    manager.dialog_data[DIALOG_FILE_ID_KEY] = file_id
    manager.dialog_data[DIALOG_FILE_TYPE_KEY] = _FileType.DOCUMENT if is_document else _FileType.PHOTO
    manager.dialog_data[DIALOG_AUTOMATIC_NAME_KEY] = sent_name or registry.generate_trivial_name()

    if file_size > FILE_SIZE_LIMIT:
        logger.info("Image rejected: file size is %d", file_size)
        manager.dialog_data[DIALOG_FAIL_REASON_KEY] = _ErrorReason.FILE_SIZE
        await manager.switch_to(UploadBackgroundStates.UPLOAD_FAILED)
        return

    bot = message.bot
    assert bot is not None, "No bot context in message"
    file = await bot.download(file_id)
    assert file is not None, "image loaded to file system"

    try:
        image = Image.open(file)
    except UnidentifiedImageError:
        logger.info("Image rejected: cannot open as image (file_id %s)", file_id)
        manager.dialog_data[DIALOG_FAIL_REASON_KEY] = _ErrorReason.UNREADABLE
        await manager.switch_to(UploadBackgroundStates.UPLOAD_FAILED)
        return

    width, height = image.size
    manager.dialog_data[DIALOG_REAL_WIDTH_KEY] = width
    manager.dialog_data[DIALOG_REAL_HEIGHT_KEY] = height
    manager.dialog_data[DIALOG_RESIZE_MODE_KEY] = "ignore"

    user = cast(UserEntity, manager.middleware_data[USER_ENTITY_KEY])
    if not user.accept_compressed and not is_document:
        await manager.switch_to(UploadBackgroundStates.UPLOADED_NOT_DOCUMENT)
    else:
        await check_dimensions(message, _, manager)


async def check_dimensions(_update: Any, _widget: Any, manager: DialogManager) -> None:
    ignore_shape_mismatch: bool = manager.start_data[START_DATA_GLOBAL_SCOPE_KEY]
    if ignore_shape_mismatch:
        logging.debug("Ignore checking dimensions")
        await manager.switch_to(UploadBackgroundStates.UPLOADED_EXPECT_NAME)
        return

    real = (manager.dialog_data[DIALOG_REAL_WIDTH_KEY], manager.dialog_data[DIALOG_REAL_HEIGHT_KEY])
    expected = (manager.dialog_data[DIALOG_EXPECTED_WIDTH_KEY], manager.dialog_data[DIALOG_EXPECTED_HEIGHT_KEY])

    if expected == (None, None):
        logger.debug("Ignore checking dimensions because no template available")
        await manager.switch_to(UploadBackgroundStates.UPLOADED_EXPECT_NAME)
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
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    registry: ElementsRegistryAbstract = manager.middleware_data[ELEMENT_REGISTRY_KEY]
    expected = (manager.dialog_data[DIALOG_EXPECTED_WIDTH_KEY], manager.dialog_data[DIALOG_EXPECTED_HEIGHT_KEY])
    resize_mode = manager.dialog_data[DIALOG_RESIZE_MODE_KEY]
    file_id = manager.dialog_data[DIALOG_FILE_ID_KEY]
    file_type = manager.dialog_data[DIALOG_FILE_TYPE_KEY]
    user_id = active_user_id(manager)
    logger.info("Saving new image: %s", data)

    if isinstance(update, CallbackQuery):
        message_to_answer = update.message if isinstance(update.message, Message) else None
    elif isinstance(update, Message):
        message_to_answer = update
    else:
        message_to_answer = None

    if user_id is None and not has_admin_privileges(manager):
        if message_to_answer:
            await message_to_answer.answer(i18n.get("notify-forbidden"))
        await manager.done()
        return

    try:
        new_element = await registry.save_element(
            None,
            user_id,
            element_name=data,
            file_id_document=file_id if file_type == _FileType.DOCUMENT else None,
            file_id_photo=file_id if file_type == _FileType.PHOTO else None,
            target_size=expected,
            resize_mode=resize_mode,
        )
    except DuplicateNameException:
        if message_to_answer:
            await message_to_answer.answer(i18n.get("notify-name_used", escaped_name=html.escape(data)))
        # Leave in the same state so that user could type another name
        return

    if message_to_answer:
        await message_to_answer.answer(i18n.get("notify-saved_image", escaped_name=html.escape(data)))
    # Since we send a custom message, dialogs should send new one to use the latest message in the chat
    await manager.done(result={RESULT_ELEMENT_ID_KEY: new_element.element_id}, show_mode=ShowMode.SEND)


async def save_image_auto_name(
    update: CallbackQuery,
    _widget: Any,
    manager: DialogManager,
):
    auto_name = manager.dialog_data[DIALOG_AUTOMATIC_NAME_KEY]
    logger.debug("Confirmed automatic name: %s", auto_name)
    return await save_image(update, _widget, manager, data=auto_name)


upload_image_window = Window(
    FluentFormat("dialog-upload-main"),
    Cancel(FluentFormat("dialog-cancel"), id="cancel_upload"),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=UploadBackgroundStates.START,
)

uploaded_not_document_window = Window(
    FluentFormat("dialog-upload-nodoc"),
    Button(FluentFormat("dialog-fine"), id="confirm_non_document_upload", on_click=check_dimensions),
    Cancel(FluentFormat("dialog-cancel"), id="cancel_upload_nodoc"),
    MessageInput(handle_image_upload, content_types=[ContentType.DOCUMENT]),
    state=UploadBackgroundStates.UPLOADED_NOT_DOCUMENT,
)

uploaded_bad_dimensions_window = Window(
    FluentFormat(
        "dialog-upload-dim.crop",
        real_width=F["dialog_data"]["real_width"],
        real_height=F["dialog_data"]["real_height"],
        expected_width=F["dialog_data"]["expected_width"],
        expected_height=F["dialog_data"]["expected_height"],
    ),
    SwitchTo(
        FluentFormat("dialog-upload-dim.resize"),
        id="bad_dimensions_resize",
        state=UploadBackgroundStates.UPLOADED_EXPECT_NAME,
        on_click=save_to_dialog_data("resize_mode", "resize"),
    ),
    SwitchTo(
        FluentFormat("dialog-upload-dim.crop"),
        id="bad_dimensions_crop",
        state=UploadBackgroundStates.UPLOADED_EXPECT_NAME,
        on_click=save_to_dialog_data("resize_mode", "crop"),
    ),
    SwitchTo(
        FluentFormat("dialog-fine"), id="bad_dimensions_ignore", state=UploadBackgroundStates.UPLOADED_EXPECT_NAME
    ),
    Cancel(FluentFormat("dialog-cancel"), id="cancel_upload_dim"),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=UploadBackgroundStates.UPLOADED_BAD_DIMENSIONS,
)

uploaded_expect_name_window = Window(
    FluentFormat("dialog-upload-name", automatic_name=F["dialog_data"]["automatic_name"]),
    TextInput(id="background_name_input", type_factory=ElementsRegistryAbstract.validate_name, on_success=save_image),
    Button(FluentFormat("dialog-fine"), id="confirm_autogenerated_name", on_click=save_image_auto_name),
    Cancel(FluentFormat("dialog-cancel"), id="cancel_upload_name"),
    state=UploadBackgroundStates.UPLOADED_EXPECT_NAME,
)

upload_failed_window = Window(
    FluentFormat("dialog-upload-fail", reason=F["dialog_data"]["fail_reason"]),
    Cancel(FluentFormat("dialog-upload-fail.accept"), id="accept_failed_upload"),
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
    name=__name__,
)
