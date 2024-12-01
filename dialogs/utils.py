import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Union, cast, ClassVar

from aiogram import Bot
from aiogram.fsm.state import State
from aiogram.types import BufferedInputFile, CallbackQuery, Message, InputFile
from aiogram_dialog import DialogManager, Data
from aiogram_dialog.api.entities import MediaAttachment, NewMessage, StartMode, ShowMode
from aiogram_dialog.manager.message_manager import MessageManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.kbd import Button, Start
from aiogram_dialog.widgets.kbd.button import OnClick
from fluentogram import TranslatorRunner
from magic_filter import MagicFilter
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot_registry.image_assets import DbElementRegistry
from database_models import User


logger = logging.getLogger(__file__)


def current_user_id(dialog_manager: DialogManager) -> int:
    user = cast(User, dialog_manager.middleware_data["user"])
    return user.tg_id


def active_user_id(dialog_manager: DialogManager) -> int | None:
    if dialog_manager.start_data and dialog_manager.start_data.get("global_scope"):
        return None
    return current_user_id(dialog_manager)


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

    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def get_media_source(
            self, media: MediaAttachment, bot: Bot,
    ) -> Union[InputFile, str]:
        if not media.file_id or not (file_id := media.file_id.file_id).startswith(self.BOT_URI_PREFIX):
            return await super().get_media_source(media, bot)

        user_id, element_id = self.parse_bot_uri(file_id)
        async with self.session_pool() as session:
            registry = DbElementRegistry(session)
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
                if file_id.startswith(self.BOT_URI_PREFIX):
                    bot_uri = media_id.file_id
                    await self.update_file_id(bot_uri, file_id)
            else:
                logger.warning("Media passed not via media_id: %s", media_info.__dict__)

        return message

    async def update_file_id(self, file_id: str, bot_uri: str) -> None:
        user_id, element_id = self.parse_bot_uri(bot_uri)
        with self.session_pool() as session:
            registry = DbElementRegistry(session)
            await registry.update_element_file_id(user_id, element_id, file_id, file_type="photo")

    @classmethod
    def parse_bot_uri(cls, bot_uri: str) -> tuple[int | None, str]:
        assert bot_uri.startswith(cls.BOT_URI_PREFIX)
        bot_uri = bot_uri.removeprefix(cls.BOT_URI_PREFIX)
        user_id, element_id = bot_uri.split("/")
        return int(user_id) or None, element_id


class StartWithData(Start):
    """
    This widget is similar to :class:`from aiogram_dialog.widgets.kbd.state.Start`,
    but re-uses start data from the current dialog instead of static data.
    If data keys are provided, only given keys are copied. If static data is provided,
    it takes priority over values from current context.
    """
    def __init__(
            self,
            text: Text,
            id: str,  # noqa
            state: State,
            data: dict | None = None,
            on_click: Optional[OnClick] = None,
            show_mode: Optional[ShowMode] = None,
            mode: StartMode = StartMode.NORMAL,
            when: WhenCondition = None,
            data_keys: list[str] | None = None,
            dialog_data_keys: list[str] | None = None,
    ):
        super().__init__(
            text=text,
            id=id,
            state=state,
            data=data,
            on_click=on_click,
            show_mode=show_mode,
            mode=mode,
            when=when,
        )
        self.data_keys = data_keys
        self.dialog_data_keys = dialog_data_keys

    async def _on_click(
            self,
            callback: CallbackQuery,
            button: Button,
            manager: DialogManager,
    ):
        if self.user_on_click:
            await self.user_on_click(callback, self, manager)

        data = {}

        if isinstance(manager.start_data, dict):
            if self.data_keys is None:
                data.update(manager.start_data)
            else:
                data.update({key: manager.start_data.get(key) for key in self.data_keys})

        if isinstance(manager.dialog_data, dict):
            if self.dialog_data_keys is None:
                # Dialog data is usually large unlike start data, so default behaviour for them is different.
                pass
            else:
                data.update({key: manager.dialog_data.get(key) for key in self.dialog_data_keys})

        if self.start_data:
            data.update(self.start_data)

        await manager.start(
            state=self.state,
            data=data,
            mode=self.mode,
            show_mode=self.show_mode,
        )


class FluentFormat(Text):
    MIDDLEWARE_KEY: ClassVar[str] = "i18n"
    def __init__(
            self, key: str,
            when: WhenCondition = None,
            **kwargs: dict[str, MagicFilter | Any]
    ):
        super().__init__(when)
        self.key = key
        self.kwargs = kwargs

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        i18n: TranslatorRunner = manager.middleware_data[self.MIDDLEWARE_KEY]
        for key, value in self.kwargs.items():
            if isinstance(value, MagicFilter):
                data[key] = value.resolve(data)
            else:
                data[key] = value

        value: str | None = i18n.get(self.key, **data)
        if value is None:
            raise ValueError(f"Missing key {self.key}")
        return value
