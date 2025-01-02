import io
import json
import logging
from typing import Any

from aiogram import Bot
from aiogram.types import ContentType, Message, BufferedInputFile
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from fluentogram import TranslatorRunner
from magic_filter import F
from pydantic import ValidationError

from bot_registry import TemplateRegistryAbstract
from services.renderer.templates import Template
from .states import TemplatesStates
from .utils import FluentFormat, current_user_id

logger = logging.getLogger(__file__)


FILE_SIZE_LIMIT = 1 * 1024 * 1024

async def on_dialog_start(_: Any, manager: DialogManager) -> None:
    template_registry: TemplateRegistryAbstract = manager.middleware_data["template_registry"]
    user_id = current_user_id(manager)
    manager.dialog_data["template"] = await template_registry.get_template(user_id)
    manager.dialog_data["global_template"] = await template_registry.get_template(None)


has_user_template = F["dialog_data"]["template"]


async def send_template(
        bot: Bot, chat_id: int, template: Template, filename: str, description: str | None = None
) -> None:
    body = template.model_dump_json(by_alias=True, exclude_none=True).encode()
    await bot.send_document(chat_id, BufferedInputFile(file=body, filename=filename), caption=description)


async def handle_new_template(
        message: Message,
        _: MessageInput,
        manager: DialogManager,
) -> None:
    i18n: TranslatorRunner = manager.middleware_data["i18n"]
    template_registry: TemplateRegistryAbstract = manager.middleware_data["template_registry"]
    bot = message.bot
    assert bot is not None, "No bot context in message"
    assert message.document is not None

    file = await bot.download(message.document.file_id)
    assert file is not None, "image loaded to file system"

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

    old_template: Template | None = manager.dialog_data["template"]
    if old_template is not None:
        logger.info("Sending back previous template")
        await send_template(
            bot,
            message.chat.id,
            old_template,
            i18n.get("notify-templates.old_filename"),
            i18n.get("notify-templates.old_description"),
        )

    await template_registry.update_template(current_user_id(manager), new_template)
    manager.dialog_data["template"] = new_template


start_window = Window(
    FluentFormat("dialog-templates", has_local=has_user_template.cast(bool).cast(int)),
    Button(FluentFormat("dialog-templates.view_user"), "download_local", when=has_user_template),  # TODO
    Button(FluentFormat("dialog-templates.view_global"), "download_global"),  # TODO
    Button(FluentFormat("dialog-templates.clear"), "clear", when=has_user_template),  # TODO
    Cancel(FluentFormat("dialog-cancel")),
    MessageInput(
        handle_new_template,
        content_types=ContentType.DOCUMENT,
        filter=F.document.file_size <= FILE_SIZE_LIMIT,
    ),
    state=TemplatesStates.START,
)


dialog = Dialog(
    start_window,
    on_start=on_dialog_start,
    name=__file__,
)
