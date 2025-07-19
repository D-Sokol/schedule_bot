import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Union, cast

from aiogram import Bot, F
from aiogram.types import BufferedInputFile, CallbackQuery, Chat, InputFile, Message
from aiogram_dialog import Data, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, NewMessage
from aiogram_dialog.manager.message_manager import MessageManager
from aiogram_dialog.widgets.kbd import Button
from fluentogram import TranslatorRunner
from nats.js import JetStreamContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.middlewares.db_session import USER_ENTITY_KEY
from app.middlewares.i18n import I18N_KEY
from bot_registry.image_elements import DbElementRegistry, ElementsRegistryAbstract
from core.entities import UserEntity

logger = logging.getLogger(__name__)


def current_user_id(dialog_manager: DialogManager) -> int:
    user = cast(UserEntity, dialog_manager.middleware_data[USER_ENTITY_KEY])
    return user.telegram_id


def active_user_id(dialog_manager: DialogManager) -> int | None:
    if isinstance(dialog_manager.start_data, dict) and dialog_manager.start_data.get("global_scope"):
        return None
    return current_user_id(dialog_manager)


def has_admin_privileges(dialog_manager: DialogManager) -> bool:
    user = cast(UserEntity, dialog_manager.middleware_data[USER_ENTITY_KEY])
    return user.is_admin


has_admin_privileges_filter = F["middleware_data"][USER_ENTITY_KEY].is_admin


def current_chat_id(dialog_manager: DialogManager) -> int:
    chat = cast(Chat, dialog_manager.middleware_data["event_chat"])
    return chat.id


def save_to_dialog_data(key: str, value: Data) -> Callable[[CallbackQuery | Message, Any, DialogManager], Awaitable]:
    async def callback(_update: CallbackQuery | Message, _widget: Any, manager: DialogManager) -> None:
        logger.debug("Saving %s = %s", key, value)
        manager.dialog_data[key] = value

    return callback


async def handler_not_implemented_button(callback: CallbackQuery, button: Button, manager: DialogManager):
    i18n: TranslatorRunner = manager.middleware_data[I18N_KEY]
    logging.warning("Called button [%s] which is not implemented!", button.widget_id)
    await callback.answer(i18n.get("notify-not_implemented"))


class BotAwareMessageManager(MessageManager):
    def __init__(self, session_pool: async_sessionmaker, js: JetStreamContext):
        self.session_pool = session_pool
        self.js = js

    async def get_media_source(
        self,
        media: MediaAttachment,
        bot: Bot,
    ) -> Union[InputFile, str]:
        if not media.file_id or not (file_id := media.file_id.file_id).startswith(
            ElementsRegistryAbstract.BOT_URI_PREFIX
        ):
            return await super().get_media_source(media, bot)

        assert file_id
        user_id, element_id = ElementsRegistryAbstract.parse_bot_uri(file_id)
        async with self.session_pool() as session:
            registry = DbElementRegistry(session=session, js=self.js)
            # We don't check existing via `.is_element_content_ready` since this is not called unless so.
            content = await registry.get_element_content(user_id or None, element_id)
            file_name = (await registry.get_element(user_id or None, element_id)).name
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
                if (bot_uri := media_id.file_id).startswith(ElementsRegistryAbstract.BOT_URI_PREFIX):
                    await self.update_file_id(file_id, bot_uri)
            else:
                logger.warning("Media passed not via media_id: %s", media_info.__dict__)

        return message

    async def update_file_id(self, file_id: str, bot_uri: str) -> None:
        user_id, element_id = ElementsRegistryAbstract.parse_bot_uri(bot_uri)
        async with self.session_pool() as session:
            registry = DbElementRegistry(session=session, js=self.js)
            await registry.update_element_file_id(user_id, element_id, file_id, file_type="photo")
