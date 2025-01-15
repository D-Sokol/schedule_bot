import asyncio
import logging

from aiogram import Bot, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import BotCommand, Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from fluentogram import TranslatorRunner, TranslatorHub

from database_models import User
from dialogs.states import MainMenuStates, BackgroundsStates, TemplatesStates, ScheduleStates, UploadBackgroundStates
from fluentogram_utils import clear_fluentogram_message

logger = logging.getLogger(__name__)

commands_router = Router(name="commands")


@commands_router.message(CommandStart())
async def start_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting main dialog from command")
    await dialog_manager.start(MainMenuStates.START, mode=StartMode.RESET_STACK)


@commands_router.message(Command("backgrounds"))
async def backgrounds_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting backgrounds (user-local) dialog from command")
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(
        BackgroundsStates.START, data={"global_scope": False, "select_only": False}, show_mode=ShowMode.SEND
    )


@commands_router.message(Command("templates"))
async def templates_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting templates dialog from command")
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(TemplatesStates.START, show_mode=ShowMode.SEND)


@commands_router.message(Command("elements"))
async def backgrounds_global_handler(message: Message, dialog_manager: DialogManager, i18n: TranslatorRunner, user: User) -> None:
    logger.info("Starting backgrounds (global scope) dialog from command")
    if not user.is_admin:
        logger.info("Editing global scope assets is blocked for user %d", user.tg_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    logger.debug("Editing global scope assets is allowed for user %d", user.tg_id)
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(
        BackgroundsStates.START, data={"global_scope": True, "select_only": False}, show_mode=ShowMode.SEND
    )


@commands_router.message(Command("upload"))
async def templates_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting templates dialog from command")
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(UploadBackgroundStates.START, show_mode=ShowMode.SEND, data={"global_scope": False})


@commands_router.message(Command("create"))
async def schedule_creation_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting creating schedule dialog from command")
    await dialog_manager.start(
        ScheduleStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(ScheduleStates.START, show_mode=ShowMode.SEND)


@commands_router.message(Command("help"))
async def help_handler(
        message: Message,
        dialog_manager: DialogManager,
        i18n: TranslatorRunner,
        source_code_url: str,
) -> None:
    help_text = i18n.get("notify-help", source_code_url=source_code_url)
    help_text = clear_fluentogram_message(help_text)  # Clearing extra symbols is required for links.
    await message.answer(help_text)
    if not dialog_manager.current_stack().empty():
        logger.debug("Showing dialog message again")
        await dialog_manager.show(ShowMode.DELETE_AND_SEND)


_BOT_COMMANDS = ["start", "backgrounds", "templates", "elements", "upload", "create", "help"]


async def set_commands(bot: Bot, hub: TranslatorHub, locales: list[str], root_locale: str | None = None) -> None:
    logger.info("Setting bot commands for locales %s", locales)
    commands: dict[str, list[BotCommand]] = {}
    for locale in locales:
        i18n = hub.get_translator_by_locale(locale)
        commands[locale] = [
            BotCommand(command=command, description=i18n.get(f"command-{command}"))
            for command in _BOT_COMMANDS
        ]
    await asyncio.gather(
        *(
            bot.set_my_commands(commands_localized, language_code=locale if locale != root_locale else None)
            for locale, commands_localized in commands.items()
        )
    )
