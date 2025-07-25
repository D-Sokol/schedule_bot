import io
import json
import logging
from functools import partial

from aiogram import Bot
from aiogram.types import BufferedInputFile, CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from fluentogram import TranslatorRunner
from magic_filter import F
from pydantic import ValidationError

from app.middlewares.i18n import I18N_KEY
from app.middlewares.registry import TEMPLATE_REGISTRY_KEY
from bot_registry.templates import TemplateRegistryAbstract
from services.renderer.templates import Template

from .custom_widgets import FluentFormat
from .states import TemplatesStates
from .utils import current_user_id

logger = logging.getLogger(__name__)

DIALOG_HAS_USER_TEMPLATE_KEY = "has_user_template"

FILE_SIZE_LIMIT = 1 * 1024 * 1024


async def send_template(
    bot: Bot, chat_id: int, template: Template, filename: str, description: str | None = None
) -> None:
    logger.debug("Send template as '%s' to chat %d", filename, chat_id)
    body = template.model_dump_json(by_alias=True, exclude_none=True).encode()
    await bot.send_document(chat_id, BufferedInputFile(file=body, filename=filename), caption=description)


async def handle_new_template(
    message: Message,
    _: MessageInput,
    manager: DialogManager,
) -> None:
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    template_registry: TemplateRegistryAbstract = manager.middleware_data[TEMPLATE_REGISTRY_KEY]
    user_id = current_user_id(manager)
    bot = message.bot
    assert bot is not None, "No bot context in message"
    assert message.document is not None

    file = await bot.download(message.document.file_id)
    assert file is not None, "image loaded to file system"
    logger.info("Got new template for %s", message.from_user.id)

    try:
        data = json.load(io.TextIOWrapper(file))
        new_template = Template.model_validate(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.info("Cannot read content as JSON")
        await message.answer(i18n.get("notify-templates.error_json"))
        return
    except ValidationError:
        logger.info("File content is not a valid template")
        await message.answer(i18n.get("notify-templates.error_validation"))
        return

    old_template: Template | None = await template_registry.get_template(user_id)
    if old_template is not None:
        logger.info("Sending back previous template")
        await send_template(
            bot,
            message.chat.id,
            old_template,
            i18n.get("notify-templates.old_filename"),
            i18n.get("notify-templates.old_description"),
        )
        manager.show_mode = ShowMode.DELETE_AND_SEND

    await template_registry.update_template(current_user_id(manager), new_template)


async def handle_download_template(
    callback: CallbackQuery,
    _widget: Button,
    manager: DialogManager,
    global_template: bool = True,
):
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    template_registry: TemplateRegistryAbstract = manager.middleware_data[TEMPLATE_REGISTRY_KEY]
    bot = callback.bot
    user_id = current_user_id(manager) if not global_template else None

    template = await template_registry.get_template(user_id)
    if template is None:
        logger.error("Cannot send missing template for %d!", user_id)
        return

    await send_template(
        bot,
        manager.middleware_data["event_chat"].id,
        template,
        i18n.get("notify-templates.local_filename"),
        i18n.get("notify-templates.local_description"),
    )
    manager.show_mode = ShowMode.DELETE_AND_SEND


async def handle_clear_template(callback: CallbackQuery, _widget: Button, manager: DialogManager):
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    template_registry: TemplateRegistryAbstract = manager.middleware_data[TEMPLATE_REGISTRY_KEY]
    bot = callback.bot
    user_id = current_user_id(manager)

    template = await template_registry.get_template(user_id)
    if template is None:
        logger.error("Cannot send missing template for %d!", user_id)
        return

    await send_template(
        bot,
        manager.middleware_data["event_chat"].id,
        template,
        i18n.get("notify-templates.old_filename"),
        i18n.get("notify-templates.old_description"),
    )
    manager.show_mode = ShowMode.DELETE_AND_SEND
    await template_registry.clear_template(user_id)


async def check_current_template_getter(
    dialog_manager: DialogManager, template_registry: TemplateRegistryAbstract, **_
) -> dict[str, bool]:
    user_id = current_user_id(dialog_manager)
    template: Template | None = await template_registry.get_template(user_id)
    return {DIALOG_HAS_USER_TEMPLATE_KEY: template is not None}


start_window = Window(
    FluentFormat("dialog-templates", has_local=F[DIALOG_HAS_USER_TEMPLATE_KEY].cast(int)),
    Button(
        FluentFormat("dialog-templates.view_user"),
        id="download_local",
        on_click=partial(handle_download_template, global_template=False),
        when=DIALOG_HAS_USER_TEMPLATE_KEY,
    ),
    Button(
        FluentFormat("dialog-templates.view_global"),
        id="download_global",
        on_click=partial(handle_download_template, global_template=True),
    ),
    Button(
        FluentFormat("dialog-templates.clear"),
        id="clear",
        when=DIALOG_HAS_USER_TEMPLATE_KEY,
        on_click=handle_clear_template,
    ),
    Cancel(FluentFormat("dialog-cancel")),
    MessageInput(
        handle_new_template,
        content_types=ContentType.DOCUMENT,
        filter=F.document.file_size <= FILE_SIZE_LIMIT,
    ),
    state=TemplatesStates.START,
    getter=check_current_template_getter,
)


dialog = Dialog(
    start_window,
    name=__name__,
)
