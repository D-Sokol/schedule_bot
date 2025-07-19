import asyncio
import logging

from aiogram import Bot, Router
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import BotCommand, Message
from aiogram_dialog import DialogManager, ShowMode
from fluentogram import TranslatorRunner, TranslatorHub

from core.entities import UserEntity
from core.fluentogram_utils import clear_fluentogram_message
from app.dialogs.states import (
    MainMenuStates,
    BackgroundsStates,
    TemplatesStates,
    ScheduleStates,
    UploadBackgroundStates,
    AdministrationStates,
    SettingsStates,
)


logger = logging.getLogger(__name__)

commands_router = Router(name="commands")


@commands_router.message(CommandStart())
async def start_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting main dialog from command")
    await dialog_manager.start(MainMenuStates.START)


@commands_router.message(Command("backgrounds"))
async def backgrounds_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting backgrounds (user-local) dialog from command")
    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(
        BackgroundsStates.START, data={"global_scope": False, "select_only": False}, show_mode=ShowMode.SEND
    )


@commands_router.message(Command("templates"))
async def templates_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting templates dialog from command")
    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(TemplatesStates.START, show_mode=ShowMode.SEND)


@commands_router.message(Command("elements"))
async def backgrounds_global_handler(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    user: UserEntity,
) -> None:
    logger.info("Starting backgrounds (global scope) dialog from command")
    if not user.is_admin:
        logger.info("Editing global scope elements is blocked for user %d", user.telegram_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    logger.debug("Editing global scope elements is allowed for user %d", user.telegram_id)
    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(
        BackgroundsStates.START, data={"global_scope": True, "select_only": False}, show_mode=ShowMode.SEND
    )


@commands_router.message(Command("upload"))
async def upload_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting templates dialog from command")
    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(UploadBackgroundStates.START, show_mode=ShowMode.SEND, data={"global_scope": False})


@commands_router.message(Command("create"))
async def schedule_creation_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting creating schedule dialog from command")
    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(ScheduleStates.START, show_mode=ShowMode.SEND)


@commands_router.message(Command("settings"))
async def settings_handler(_: Message, dialog_manager: DialogManager) -> None:
    logger.info("Starting settings dialog from command")
    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(SettingsStates.START, show_mode=ShowMode.SEND)


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


@commands_router.message(Command("grant"))
async def grant_handler(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    user: UserEntity,
    command: CommandObject,
) -> None:
    if not user.is_admin:
        logger.info("Refuse to grant someone for user %d", user.telegram_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    start_data: dict = {"action": "grant_admin"}
    if command.args is not None:
        try:
            target_id = int(command.args)
            if target_id <= 0:
                raise ValueError("User id must be positive!")
            start_data["user_id"] = target_id
        except ValueError:
            logger.info("Could not understand grant command: %s", command.args)
            await message.answer(i18n.get("command-grant.unparsed"))
            return

    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(AdministrationStates.START, data=start_data, show_mode=ShowMode.SEND)


@commands_router.message(Command("revoke"))
async def revoke_handler(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    user: UserEntity,
    command: CommandObject,
) -> None:
    if not user.is_admin:
        logger.info("Refuse to revoke someone for user %d", user.telegram_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    start_data: dict = {"action": "revoke_admin"}
    if command.args is not None:
        try:
            target_id = int(command.args)
            if target_id <= 0:
                raise ValueError("User id must be positive!")
            start_data["user_id"] = target_id
        except ValueError:
            logger.info("Could not understand revoke command: %s", command.args)
            await message.answer(i18n.get("command-revoke.unparsed"))
            return

    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(AdministrationStates.START, data=start_data, show_mode=ShowMode.SEND)


@commands_router.message(Command("ban"))
async def ban_handler(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    user: UserEntity,
    command: CommandObject,
) -> None:
    if not user.is_admin:
        logger.info("Refuse to ban someone for user %d", user.telegram_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    start_data: dict = {"action": "ban_user"}
    if command.args is not None:
        try:
            target_id = int(command.args)
            if target_id <= 0:
                raise ValueError("User id must be positive!")
            start_data["user_id"] = target_id
        except ValueError:
            logger.info("Could not understand ban command: %s", command.args)
            await message.answer(i18n.get("command-ban.unparsed"))
            return

    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(AdministrationStates.START, data=start_data, show_mode=ShowMode.SEND)


@commands_router.message(Command("unban"))
async def unban_handler(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    user: UserEntity,
    command: CommandObject,
) -> None:
    if not user.is_admin:
        logger.info("Refuse to unban someone for user %d", user.telegram_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    start_data: dict = {"action": "unban_user"}
    if command.args is not None:
        try:
            target_id = int(command.args)
            if target_id <= 0:
                raise ValueError("User id must be positive!")
            start_data["user_id"] = target_id
        except ValueError:
            logger.info("Could not understand unban command: %s", command.args)
            await message.answer(i18n.get("command-unban.unparsed"))
            return

    await dialog_manager.start(MainMenuStates.START, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(AdministrationStates.START, data=start_data, show_mode=ShowMode.SEND)


_BOT_COMMANDS = [
    "start",
    "backgrounds",
    "templates",
    "elements",
    "upload",
    "create",
    "settings",
    "help",
    "grant",
    "revoke",
    "ban",
    "unban",
]


async def set_commands(bot: Bot, hub: TranslatorHub, locales: list[str], root_locale: str | None = None) -> None:
    logger.info("Setting bot commands for locales %s", locales)
    commands: dict[str, list[BotCommand]] = {}
    for locale in locales:
        i18n = hub.get_translator_by_locale(locale)
        commands[locale] = [
            BotCommand(command=command, description=i18n.get(f"command-{command}")) for command in _BOT_COMMANDS
        ]
    await asyncio.gather(
        *(
            bot.set_my_commands(commands_localized, language_code=locale if locale != root_locale else None)
            for locale, commands_localized in commands.items()
        )
    )
