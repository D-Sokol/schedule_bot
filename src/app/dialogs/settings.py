import logging
from typing import cast

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Cancel, Radio, Button, Checkbox, ManagedCheckbox, ManagedRadio

from bot_registry.users import UserRegistryAbstract
from core.entities import PreferredLanguage
from .custom_widgets import FluentFormat
from .states import SettingsStates
from .utils import current_user_id

logger = logging.getLogger(__name__)


async def confirm_save(_callback: CallbackQuery, _widget: Button, manager: DialogManager):
    user_registry: UserRegistryAbstract = manager.middleware_data["user_registry"]
    user_id = current_user_id(manager)
    allow_uncompressed = cast(ManagedCheckbox, manager.find("accept_uncompressed")).is_checked()
    preferred_language = cast(ManagedRadio[PreferredLanguage], manager.find("language")).get_checked()
    logger.info(
        "Saving settings for user %d: allow_uncompressed=%s, preferred_language=%s",
        user_id,
        allow_uncompressed,
        preferred_language,
    )

    await user_registry.set_user_compressed_warning(user_id, allow_uncompressed)
    if preferred_language is not None:
        await user_registry.set_user_language(user_id, preferred_language)


start_window = Window(
    FluentFormat("dialog-settings"),
    Radio(
        FluentFormat("dialog-settings.language", checked=1, language=F["item"]),
        FluentFormat("dialog-settings.language", checked=0, language=F["item"]),
        id="language",
        items=list(PreferredLanguage),
        item_id_getter=str,
        type_factory=PreferredLanguage,
    ),  # TODO: update on start
    Checkbox(
        FluentFormat("dialog-settings.accept_uncompressed_checked"),
        FluentFormat("dialog-settings.accept_uncompressed_unchecked"),
        id="accept_uncompressed",
        default=False,  # TODO: update on start
    ),
    Button(
        FluentFormat("dialog-settings.apply"),
        on_click=confirm_save,
        id="apply",
    ),
    Cancel(
        FluentFormat("dialog-settings.confirm"),
        on_click=confirm_save,
        id="confirm",
    ),
    Cancel(FluentFormat("dialog-cancel")),
    state=SettingsStates.START,
)


dialog = Dialog(
    start_window,
    name=__name__,
)
