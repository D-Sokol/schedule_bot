import asyncio
import logging
import nats
import os
import sqlalchemy
from contextlib import suppress
from typing import cast

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ErrorEvent
from aiogram_dialog import DialogManager, setup_dialogs
from aiogram_dialog.api.exceptions import UnknownIntent
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot_registry.users import DbUserRegistry
from db_middleware import DbSessionMiddleware
from i18n_middleware import TranslatorRunnerMiddleware, create_translator_hub
from dialogs import all_dialogs
from dialogs.main_menu import MainMenuStates as MainMenuStates
from dialogs.utils import BotAwareMessageManager

from converter import convert


dialogs_router = Router(name="start")


@dialogs_router.message(CommandStart())
async def handler(_: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MainMenuStates.START)


# This handler must be registered via DP instead of `dialogs_router`
async def handle_old_button(event: ErrorEvent, i18n: TranslatorRunner) -> None:
    exc = cast(UnknownIntent, event.exception)
    logging.info("Old button used: %s", exc)
    if (callback_query := event.update.callback_query) is not None:
        with suppress(TelegramBadRequest):
            await callback_query.answer(i18n.get("notify-unknown_intent"))
            await callback_query.message.delete()
    else:
        logging.warning(
            "Unknown Intent for non-callback type: %s",
            event.model_dump_json(exclude_none=True, exclude_defaults=True, exclude_unset=True),
        )


async def main(
        token: str,
        db_url: str,
        nats_servers: str,
        log_level: str = "WARNING",
        admin_id: int = -1,
) -> None:
    engine = create_async_engine(db_url, echo=(log_level == "DEBUG"))
    session_pool = async_sessionmaker(engine, expire_on_commit=False)
    if admin_id > 0:
        # Register user and grant him admin privileges AND check db connection
        async with session_pool() as session:
            user_registry = DbUserRegistry(session)
            await user_registry.get_or_create_user(admin_id, create_admin=True)
        logging.info("User %d promoted to admins", admin_id)
    else:
        # Just check db connection
        async with session_pool() as session:
            _ = await session.execute(sqlalchemy.select(1))
    logging.info("Successfully connected to DB")

    nc = await nats.connect(servers=nats_servers)
    js = nc.jetstream()
    logging.info("Connected to NATS")

    db_middleware = DbSessionMiddleware(session_pool, js)
    message_manager = BotAwareMessageManager(session_pool, js)

    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    tr_middleware = TranslatorRunnerMiddleware(create_translator_hub())

    dp.message.middleware(tr_middleware)
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(tr_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.errors.middleware(tr_middleware)

    dp.include_router(dialogs_router)
    dp.include_routers(*all_dialogs)
    dp.error.register(handle_old_button, ExceptionTypeFilter(UnknownIntent))
    setup_dialogs(dp, message_manager=message_manager)
    logging.info("Starting bot")
    await bot.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        dp.start_polling(bot),
        convert(js),  # TODO: launch as a separate process.
    )


if __name__ == '__main__':
    bot_token = os.getenv("TOKEN")
    database_url = os.getenv("DB_URL")
    admin_tg_id = int(os.getenv("ADMIN_ID") or -1)
    nats_servers_ = os.getenv("NATS_SERVERS")
    if None in (bot_token, database_url, nats_servers_):
        logging.fatal("Cannot run instance without bot token, database url or nats url!")
        exit(2)
    log_level_ = os.getenv("LOG_LEVEL", "WARNING")
    logging.basicConfig(
        level=log_level_,
        format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s'
    )
    asyncio.run(main(bot_token, database_url, nats_servers_, log_level=log_level_, admin_id=admin_tg_id))
