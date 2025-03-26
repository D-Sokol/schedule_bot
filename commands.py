import asyncio
import logging
from typing import cast

from aiogram import Bot, Router, F
from aiogram.enums import MessageOriginType
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BotCommand, Message, MessageOriginUser
from aiogram_dialog import DialogManager, StartMode, ShowMode
from fluentogram import TranslatorRunner, TranslatorHub

from bot_registry import UserRegistryAbstract
from database_models import User
from dialogs.states import MainMenuStates, BackgroundsStates, TemplatesStates, ScheduleStates, UploadBackgroundStates
from fluentogram_utils import clear_fluentogram_message

logger = logging.getLogger(__name__)

commands_router = Router(name="commands")


@commands_router.message(CommandStart())
async def start_handler(_: Message, dialog_manager: DialogManager, state: FSMContext) -> None:
    logger.info("Starting main dialog from command")
    await state.set_state(None)
    await dialog_manager.start(MainMenuStates.START, mode=StartMode.RESET_STACK)


@commands_router.message(Command("backgrounds"))
async def backgrounds_handler(_: Message, dialog_manager: DialogManager, state: FSMContext) -> None:
    logger.info("Starting backgrounds (user-local) dialog from command")
    await state.set_state(None)
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(
        BackgroundsStates.START, data={"global_scope": False, "select_only": False}, show_mode=ShowMode.SEND
    )


@commands_router.message(Command("templates"))
async def templates_handler(_: Message, dialog_manager: DialogManager, state: FSMContext) -> None:
    logger.info("Starting templates dialog from command")
    await state.set_state(None)
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(TemplatesStates.START, show_mode=ShowMode.SEND)


@commands_router.message(Command("elements"))
async def backgrounds_global_handler(
        message: Message,
        dialog_manager: DialogManager,
        i18n: TranslatorRunner,
        user: User,
        state: FSMContext,
) -> None:
    logger.info("Starting backgrounds (global scope) dialog from command")
    await state.set_state(None)
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
async def templates_handler(_: Message, dialog_manager: DialogManager, state: FSMContext) -> None:
    logger.info("Starting templates dialog from command")
    await state.set_state(None)
    await dialog_manager.start(
        MainMenuStates.START, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE
    )
    await dialog_manager.start(UploadBackgroundStates.START, show_mode=ShowMode.SEND, data={"global_scope": False})


@commands_router.message(Command("create"))
async def schedule_creation_handler(_: Message, dialog_manager: DialogManager, state: FSMContext) -> None:
    logger.info("Starting creating schedule dialog from command")
    await state.set_state(None)
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
        state: FSMContext,
) -> None:
    help_text = i18n.get("notify-help", source_code_url=source_code_url)
    help_text = clear_fluentogram_message(help_text)  # Clearing extra symbols is required for links.
    await message.answer(help_text)
    await state.set_state(None)
    if not dialog_manager.current_stack().empty():
        logger.debug("Showing dialog message again")
        await dialog_manager.show(ShowMode.DELETE_AND_SEND)


class HandlingAdminPrivilegesStates(StatesGroup):
    forward_grant = State()
    forward_revoke = State()


@commands_router.message(Command("grant"))
async def grant_handler(
        message: Message,
        dialog_manager: DialogManager,
        i18n: TranslatorRunner,
        user: User,
        user_registry: UserRegistryAbstract,
        command: CommandObject,
        state: FSMContext,
) -> None:
    if not user.is_admin:
        logger.info("Refuse to grant someone for user %d", user.tg_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    if command.args is None:
        logger.info("Await message from %d to grant privileges", user.tg_id)
        await dialog_manager.reset_stack()
        await message.answer(i18n.get("command-grant.forward"))
        await state.set_state(HandlingAdminPrivilegesStates.forward_grant)
        return

    try:
        tg_id = int(command.args)
        if tg_id <= 0:
            raise ValueError("User id must be positive!")
    except ValueError:
        logger.info("Could not understand grant command: %s", command.args)
        await message.answer(i18n.get("command-grant.unparsed"))
        return

    logger.info("Grant admin privileges for %d due to %d command", tg_id, user.tg_id)
    await user_registry.grant_admin(tg_id)
    await message.answer(i18n.get("command-grant.success"))



@commands_router.message(Command("revoke"))
async def revoke_handler(
        message: Message,
        dialog_manager: DialogManager,
        i18n: TranslatorRunner,
        user: User,
        user_registry: UserRegistryAbstract,
        command: CommandObject,
        state: FSMContext,
) -> None:
    if not user.is_admin:
        logger.info("Refuse to revoke someone for user %d", user.tg_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    if command.args is None:
        logger.info("Await message from %d to revoke privileges", user.tg_id)
        await dialog_manager.reset_stack()
        await message.answer(i18n.get("command-revoke.forward"))
        await state.set_state(HandlingAdminPrivilegesStates.forward_revoke)
        return

    try:
        tg_id = int(command.args)
        if tg_id <= 0:
            raise ValueError("User id must be positive!")
    except ValueError:
        logger.info("Could not understand revoke command: %s", command.args)
        await message.answer(i18n.get("command-revoke.unparsed"))
        return

    logger.info("Revoke admin privileges for %d due to %d command", tg_id, user.tg_id)
    await user_registry.revoke_admin(tg_id)
    await message.answer(i18n.get("command-revoke.success"))


@commands_router.message(HandlingAdminPrivilegesStates.forward_grant, F.forward_origin.type == MessageOriginType.USER)
async def grant_by_forward_handler(
        message: Message,
        i18n: TranslatorRunner,
        user: User,
        user_registry: UserRegistryAbstract,
):
    if not user.is_admin:
        logger.info("Refuse to grant someone for user %d", user.tg_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    tg_id = cast(MessageOriginUser, message.forward_origin).sender_user.id
    await user_registry.grant_admin(tg_id)
    await message.answer(i18n.get("command-grant.success"))


@commands_router.message(HandlingAdminPrivilegesStates.forward_revoke, F.forward_origin.type == MessageOriginType.USER)
async def revoke_by_forward_handler(
        message: Message,
        i18n: TranslatorRunner,
        user: User,
        user_registry: UserRegistryAbstract,
):
    if not user.is_admin:
        logger.info("Refuse to revoke someone for user %d", user.tg_id)
        await message.answer(i18n.get("notify-forbidden"))
        return

    tg_id = cast(MessageOriginUser, message.forward_origin).sender_user.id
    await user_registry.revoke_admin(tg_id)
    await message.answer(i18n.get("command-revoke.success"))


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
