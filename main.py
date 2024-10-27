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

from dialog_menu import States as MainMenuStates, dialog as main_menu


dialogs_handler = Router(name="start")


@dialogs_handler.message(CommandStart())
async def handler(_: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MainMenuStates.START)


async def handle_old_button(event: ErrorEvent) -> None:
    exc = cast(UnknownIntent, event.exception)
    logging.info("Old button used: %s", exc)
    if event.update.callback_query:
        await event.update.callback_query.answer()


async def main(token: str) -> None:
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(dialogs_handler)
    dp.include_router(main_menu)
    dp.error.register(handle_old_button, ExceptionTypeFilter(UnknownIntent))
    setup_dialogs(dp)
    logging.info("Starting bot")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    bot_token = os.getenv("TOKEN")
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s'
    )
    asyncio.run(main(bot_token))
