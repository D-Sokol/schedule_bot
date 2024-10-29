import logging
from PIL import UnidentifiedImageError, Image
from datetime import datetime
from typing import Any, cast

from aiogram.filters.state import State, StatesGroup
from aiogram.types import ContentType, Message

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.text import Const, Format, Case
from aiogram_dialog.widgets.kbd import Button, Cancel, ListGroup, SwitchTo
from magic_filter import F, MagicFilter

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


async def on_dialog_start(_: Any, manager: DialogManager):
    manager.dialog_data.update({
        "expected_width": 1280,
        "expected_height": 720,
    })


async def saved_backs_getter(**_) -> dict[str, Any]:
    items = [
        {"name": "Фон 1", "id": 1},
        {"name": "Фон 2", "id": 2},
        {"name": "Фон с названием, созданным автоматически, без ручного ввода, от двадцать девятого октября две тысячи четвертого года нашей эры", "id": 3},
        {"name": "Фон 4", "id": 4},
        {"name": "Фон 4", "id": 5},
        # {"name": "Фон 6", "id": 6},
    ]
    backgrounds_limit = BACKGROUNDS_LIMIT
    logger.debug("Getter: %d images found with limit %d", len(items), backgrounds_limit)
    return {
        "items": items,
        "n_backgrounds": len(items),
        "limit": backgrounds_limit,
    }


async def crop_image(
        _update: Any, _widget: Any, manager: DialogManager,
):
    image: Image.Image = manager.dialog_data["document"]
    expected= (manager.dialog_data["expected_width"], manager.dialog_data["expected_height"])
    box = cast(tuple[int, int, int, int], (0, 0, *expected))
    image = image.crop(box)  # TODO: set fill color
    manager.dialog_data["document"] = image


async def resize_image(
        _update: Any, _widget: Any, manager: DialogManager,
):
    image: Image.Image = manager.dialog_data["document"]
    expected = (manager.dialog_data["expected_width"], manager.dialog_data["expected_height"])
    image = image.resize(expected)
    manager.dialog_data["document"] = image


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
        _update: Any,
        _widget: Any,
        manager: DialogManager,
        data: str,
):
    image: Image.Image = manager.dialog_data["document"]
    image_name = data
    logger.info("Saving %s (size %s) as '%s'", image, image.size, image_name)
    # TODO: save image
    # TODO: inform user
    await manager.switch_to(BackgroundsStates.START)


async def save_image_auto_name(
        _update: Any,
        _widget: Any,
        manager: DialogManager,
):
    auto_name = manager.dialog_data["automatic_name"]
    return await save_image(_update, _widget, manager, data=auto_name)


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
    ListGroup(
        Button(Format("🖼️ {item[name]}"), id="background"),
        id="select_background",
        item_id_getter=F["id"].resolve,
        items="items",
        when=has_backgrounds_condition,
    ),  # TODO: scrollable! See FAQ: "Create Select widget and wrap it with ScrollingGroup."
    SwitchTo(Const("Загрузить фон"), id="upload_background", state=BackgroundsStates.UPLOAD_IMAGE, when=can_upload_background_condition),
    Cancel(Const("Отставеть!")),  # FIXME: does not work as intended
    state=BackgroundsStates.START,
    getter=saved_backs_getter,
)

upload_image_window = Window(
    Const("Загрузите изображение для использования в качестве фона."),
    Const("Советую отправить картинку как файл, чтобы избежать потери качества!"),
    SwitchTo(Const("Отставеть!"), id="cancel_upload", state=BackgroundsStates.START),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=BackgroundsStates.UPLOAD_IMAGE,
)

uploaded_not_document_window = Window(
    Const("Вы отправили картинку не как файл. Это может привести к потере качества. Можете загрузить картинку еще раз?"),
    Button(Const("И так сойдет"), id="confirm_non_document_upload", on_click=check_dimensions),
    SwitchTo(Const("Отставеть!"), id="cancel_upload_nodoc", state=BackgroundsStates.START),
    MessageInput(handle_image_upload, content_types=[ContentType.DOCUMENT]),
    state=BackgroundsStates.UPLOADED_NOT_DOCUMENT,
)

uploaded_bad_dimensions_window = Window(
    Format(
        "Размер загруженного изображения ({dialog_data[real_width]}x{dialog_data[real_height]}) "
        "отличается от ожидаемого ({dialog_data[expected_width]}x{dialog_data[expected_height]})"
    ),
    Const("Вы можете загрузить другую картинку или все равно использовать эту."),
    SwitchTo(Const("Растянуть до нужного размера"), id="bad_dimensions_resize", state=BackgroundsStates.UPLOADED_EXPECT_NAME, on_click=resize_image),
    SwitchTo(Const("Обрезать картинку"), id="bad_dimensions_crop", state=BackgroundsStates.UPLOADED_EXPECT_NAME, on_click=crop_image),
    SwitchTo(Const("И так сойдет"), id="bad_dimensions_ignore", state=BackgroundsStates.UPLOADED_EXPECT_NAME),
    SwitchTo(Const("Отставеть!"), id="cancel_upload_dim", state=BackgroundsStates.START),
    MessageInput(handle_image_upload, content_types=[ContentType.PHOTO, ContentType.DOCUMENT]),
    state=BackgroundsStates.UPLOADED_BAD_DIMENSIONS,
)

uploaded_expect_name_window = Window(
    Const("Введите имя для этой картинки, чтобы потом узнать ее в списке!"),
    Format("По умолчанию картинка будет называться {dialog_data[automatic_name]}."),
    TextInput(id="background_name_input", on_success=save_image),
    Button(Const("И так сойдет"), id="confirm_autogenerated_name", on_click=save_image_auto_name),
    SwitchTo(Const("Отставеть!"), id="cancel_upload_name", state=BackgroundsStates.START),
    state=BackgroundsStates.UPLOADED_EXPECT_NAME,
)

upload_failed_window = Window(
    Const(
        "Размер этого файла слишком большой. Возможно, это и не картинка вовсе.",
        when=FILE_SIZE_ERROR_REASON == F["fail_reason"],  # FIXME: always False
    ),
    Const(
        "Не удалось открыть присланный файл как изображение.",
        when=UNREADABLE_ERROR_REASON == F["fail_reason"],  # FIXME: always False
    ),
    Format("Debug: {dialog_data[fail_reason]}"),
    SwitchTo(Const("Смириться"), id="accept_failed_upload", state=BackgroundsStates.START),
    state=BackgroundsStates.UPLOAD_FAILED,
)

selected_image_window = Window(
    Const("Здесь вы сможете увидеть изображение"),
    state=BackgroundsStates.SELECTED_IMAGE,
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
