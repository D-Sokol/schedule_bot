import asyncio
import logging
import os
from contextlib import suppress
from typing import cast

import nats
import sqlalchemy
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from aiogram_dialog import DialogManager, setup_dialogs
from aiogram_dialog.api.exceptions import OutdatedIntent, UnknownIntent
from fluentogram import TranslatorHub, TranslatorRunner
from nats.js import JetStreamContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.dialogs import all_dialogs
from app.dialogs.states import MainMenuStates
from app.dialogs.utils import BotAwareMessageManager
from app.handlers.commands import commands_router, set_commands
from app.i18n import all_translator_locales, create_translator_hub, root_locale
from app.middlewares.blacklist import BlacklistMiddleware
from app.middlewares.db_session import DbSessionMiddleware
from app.middlewares.i18n import TranslatorRunnerMiddleware
from app.middlewares.registry import RegistryMiddleware
from bot_registry.users import DbUserRegistry


# This handler must be registered via DP instead of `dialogs_router`
async def handle_old_button(event: ErrorEvent, i18n: TranslatorRunner, dialog_manager: DialogManager) -> None:
    exc = cast(UnknownIntent, event.exception)
    logging.info("Old button used: %s", exc)
    if (callback_query := event.update.callback_query) is not None:
        with suppress(TelegramBadRequest, AttributeError):
            await callback_query.answer(i18n.get("notify-unknown_intent"))
            await callback_query.message.delete()  # type: ignore[union-attr]
    else:
        logging.error(
            "Unknown Intent for non-callback type: %s",
            # Cannot use model_dump_json since exceptions are usually not JSON-serializable
            event.model_dump(exclude_none=True, exclude_defaults=True, exclude_unset=True),
        )

    if dialog_manager.current_stack().empty():
        await dialog_manager.start(MainMenuStates.START)


async def _shutdown(shutdown_event: asyncio.Event):
    shutdown_event.set()


async def setup_db(db_url: str, admin_id: int = -1, log_level: str = "WARNING") -> async_sessionmaker:
    engine = create_async_engine(db_url, echo=(log_level == "DEBUG"))
    session_pool = async_sessionmaker(engine, expire_on_commit=False)
    if admin_id > 0:
        # Register user and grant him admin privileges AND check db connection
        async with session_pool() as session:
            user_registry = DbUserRegistry(session)
            await user_registry.grant_admin(admin_id)
        logging.info("User %d promoted to admins", admin_id)
    else:
        # Just check db connection
        async with session_pool() as session:
            _ = await session.execute(sqlalchemy.select(1))
    return session_pool


async def setup_middlewares(
    dp: Dispatcher, session_pool: async_sessionmaker, js: JetStreamContext, hub: TranslatorHub
) -> None:
    db_middleware = DbSessionMiddleware(session_pool)
    registry_middleware = RegistryMiddleware(js)
    message_manager = BotAwareMessageManager(session_pool, js)

    tr_middleware = TranslatorRunnerMiddleware(hub)
    bl_middleware = BlacklistMiddleware()

    dp.message.middleware(db_middleware)
    dp.message.middleware(bl_middleware)
    dp.message.middleware(tr_middleware)
    dp.message.middleware(registry_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.callback_query.middleware(bl_middleware)
    dp.callback_query.middleware(tr_middleware)
    dp.callback_query.middleware(registry_middleware)
    dp.errors.middleware(db_middleware)
    # blacklist middleware is probably useless in error handling?
    dp.errors.middleware(tr_middleware)
    dp.errors.middleware(registry_middleware)

    dp.include_router(commands_router)
    dp.include_routers(*all_dialogs)
    dp.error.register(handle_old_button, ExceptionTypeFilter(UnknownIntent, OutdatedIntent))
    setup_dialogs(dp, message_manager=message_manager)


async def main(
    token: str,
    db_url: str,
    nats_servers: str,
    source_code_url: str,
    log_level: str = "WARNING",
    admin_id: int = -1,
) -> None:
    session_pool = await setup_db(db_url, admin_id, log_level)
    logging.info("Connected to DB")

    nc = await nats.connect(servers=nats_servers)
    js = nc.jetstream()
    logging.info("Connected to NATS")

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp["source_code_url"] = source_code_url
    hub = create_translator_hub()
    hub_locales = all_translator_locales()
    await setup_middlewares(dp, session_pool, js, hub)
    logging.info("Created middlewares")

    shutdown_event = asyncio.Event()
    dp["shutdown_event"] = shutdown_event
    dp.shutdown.register(_shutdown)

    dp["primary_admin_id"] = admin_id

    logging.info("Setting up bot...")
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    await set_commands(bot, hub=hub, locales=hub_locales, root_locale=root_locale())
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Starting bot...")
    await dp.start_polling(bot)


def entry():
    bot_token = os.getenv("TOKEN")
    database_url = os.getenv("DB_URL")
    admin_tg_id = int(os.getenv("ADMIN_ID") or -1)
    nats_servers_ = os.getenv("NATS_SERVERS")
    source_code_url_ = os.getenv("SOURCE_CODE_URL")
    if bot_token is None:
        logging.critical("Cannot run without bot token")
        exit(2)
    if database_url is None:
        logging.critical("Cannot run without database url")
        exit(2)
    if nats_servers_ is None:
        logging.critical("Cannot run instance without nats url")
        exit(2)
    if source_code_url_ is None:
        logging.critical("Please provide an url to source code repository according to license requirements")
        exit(2)
    log_level_ = os.getenv("LOG_LEVEL", "WARNING")
    logging.basicConfig(
        level=log_level_,
        format="{filename}:{lineno} #{levelname:8} [{asctime}] - {name} - {message}",
        style="{",
    )
    asyncio.run(
        main(
            bot_token,
            database_url,
            nats_servers_,
            log_level=log_level_,
            admin_id=admin_tg_id,
            source_code_url=source_code_url_,
        )
    )


if __name__ == "__main__":
    entry()
