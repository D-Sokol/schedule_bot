import asyncio
import logging
import os
from typing import cast

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ErrorEvent
from aiogram_dialog import DialogManager, setup_dialogs
from aiogram_dialog.api.exceptions import UnknownIntent

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from db_middleware import DbSessionMiddleware
from dialogs import all_dialogs
from dialogs.main_menu import MainMenuStates as MainMenuStates
from dialogs.utils import BotAwareMessageManager


dialogs_handler = Router(name="start")


@dialogs_handler.message(CommandStart())
async def handler(_: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MainMenuStates.START)


async def handle_old_button(event: ErrorEvent) -> None:
    exc = cast(UnknownIntent, event.exception)
    logging.info("Old button used: %s", exc)
    if (callback_query := event.update.callback_query) is not None:
        await callback_query.answer("Эта кнопка слишком старая. Я даже не помню, о чем мы говорили!")
        await callback_query.message.delete()  # TODO: handle error for deletion after 48 hours
    else:
        logging.warning(
            "Unknown Intent for non-callback type: %s",
            event.model_dump_json(exclude_none=True, exclude_defaults=True, exclude_unset=True),
        )


async def main(token: str, db_url: str) -> None:
    engine = create_async_engine(db_url, echo=True)
    session_pool = async_sessionmaker(engine, expire_on_commit=False)
    db_middleware = DbSessionMiddleware(session_pool)
    message_manager = BotAwareMessageManager(session_pool)

    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)

    dp.include_router(dialogs_handler)
    dp.include_routers(*all_dialogs)
    dp.error.register(handle_old_button, ExceptionTypeFilter(UnknownIntent))
    setup_dialogs(dp, message_manager=message_manager)
    logging.info("Starting bot")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    bot_token = os.getenv("TOKEN")
    database_url = os.getenv("DB_URL", "sqlite://")
    log_level = os.getenv("LOG_LEVEL")
    logging.basicConfig(
        level=log_level,
        format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s'
    )
    asyncio.run(main(bot_token, database_url))
