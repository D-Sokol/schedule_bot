import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Union

from aiogram import Bot
from aiogram.types import BufferedInputFile, CallbackQuery, Message, InputFile

from aiogram_dialog import DialogManager, Data
from aiogram_dialog.api.entities import MediaAttachment, NewMessage
from aiogram_dialog.manager.message_manager import MessageManager
from aiogram_dialog.widgets.kbd import Button

from elements_registry import ElementsRegistryAbstract


logger = logging.getLogger(__file__)


def save_to_dialog_data(key: str, value: Data) -> Callable[[CallbackQuery | Message, Any, DialogManager], Awaitable]:
    async def callback(_update: CallbackQuery | Message, _widget: Any, manager: DialogManager) -> None:
        logger.debug("Saving %s = %s", key, value)
        manager.dialog_data[key] = value
    return callback


async def not_implemented_button_handler(callback: CallbackQuery, button: Button, _manager: DialogManager):
    logging.warning("Called button [%s] which is not implemented!", button.widget_id)
    await callback.answer("Функционал не реализован.")


class BotAwareMessageManager(MessageManager):
    BOT_URI_PREFIX = "bot://"

    elements_registry: ElementsRegistryAbstract

    def __init__(self, elements_registry: ElementsRegistryAbstract):
        self.elements_registry = elements_registry

    async def get_media_source(
            self, media: MediaAttachment, bot: Bot,
    ) -> Union[InputFile, str]:
        if not media.file_id or not (file_id := media.file_id.file_id).startswith(self.BOT_URI_PREFIX):
            return await super().get_media_source(media, bot)

        user_id, element_id = self.parse_bot_uri(file_id)
        content = await self.elements_registry.get_element_content(user_id or None, element_id)
        file_name = (await self.elements_registry.get_element(user_id or None, element_id)).name
        input_document = BufferedInputFile(content, filename=str(Path(file_name).with_suffix(".png")))
        return input_document

    # Widget DynamicMedia caches file_id by our URI. Nevertheless, we explicitly save file_id in the registry,
    # just as for documents, because we can.
    async def send_media(self, bot: Bot, new_message: NewMessage) -> Message:
        message = await super().send_media(bot, new_message)

        if (photo_sizes := message.photo) is not None and (media_info := new_message.media) is not None:
            file_id = photo_sizes[-1].file_id
            media_id = media_info.file_id
            if media_id is not None:
                if file_id.startswith(self.BOT_URI_PREFIX):
                    bot_uri = media_id.file_id
                    await self.update_file_id(bot_uri, file_id)
            else:
                logger.warning("Media passed not via media_id: %s", media_info.__dict__)

        return message

    async def update_file_id(self, file_id: str, bot_uri: str) -> None:
        user_id, element_id = self.parse_bot_uri(bot_uri)
        await self.elements_registry.update_element_file_id(user_id, element_id, file_id, file_type="photo")

    @classmethod
    def parse_bot_uri(cls, bot_uri: str) -> tuple[int | None, int]:
        assert bot_uri.startswith(cls.BOT_URI_PREFIX)
        bot_uri = bot_uri.removeprefix(cls.BOT_URI_PREFIX)
        user_id, element_id = bot_uri.split("/")
        return int(user_id) or None, int(element_id)
