import logging
from typing import cast

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Checkbox,
    ManagedCheckbox,
    ManagedRadio,
    Radio,
)
from fluentogram import TranslatorHub

from app.middlewares.db_session import USER_ENTITY_KEY, USER_REGISTRY_KEY
from app.middlewares.i18n import I18N_KEY, TRANSLATOR_HUB_KEY, USED_LOCALE_KEY
from bot_registry.users import UserRegistryAbstract
from core.entities import PreferredLanguage, UserEntity

from .custom_widgets import FluentFormat
from .states import SettingsStates
from .utils import current_user_id

logger = logging.getLogger(__name__)

WIDGET_ACCEPT_UNCOMPRESSED = "accept_uncompressed"
WIDGET_LANGUAGE_SELECT = "language"


async def confirm_save(_callback: CallbackQuery, _widget: Button, manager: DialogManager):
    user_registry: UserRegistryAbstract = manager.middleware_data[USER_REGISTRY_KEY]
    user_id = current_user_id(manager)
    allow_uncompressed = cast(ManagedCheckbox, manager.find(WIDGET_ACCEPT_UNCOMPRESSED)).is_checked()
    preferred_language = cast(ManagedRadio[PreferredLanguage], manager.find(WIDGET_LANGUAGE_SELECT)).get_checked()
    logger.info(
        "Saving settings for user %d: allow_uncompressed=%s, preferred_language=%s",
        user_id,
        allow_uncompressed,
        preferred_language,
    )

    await user_registry.set_user_compressed_warning(user_id, allow_uncompressed)
    used_language = manager.middleware_data[USED_LOCALE_KEY]
    if preferred_language is not None:
        await user_registry.set_user_language(user_id, preferred_language)
        if preferred_language != used_language:
            # We need to manually update the translator in the middleware data
            # since edited message will be rendered with previous one
            # as it is a part of handling the same Telegram update.
            hub = cast(TranslatorHub, manager.middleware_data[TRANSLATOR_HUB_KEY])
            new_i18n = hub.get_translator_by_locale(preferred_language)
            manager.middleware_data[I18N_KEY] = new_i18n
            await manager.show(show_mode=ShowMode.EDIT)


start_window = Window(
    FluentFormat("dialog-settings"),
    Radio(
        FluentFormat("dialog-settings.language", checked=1, language=F["item"]),
        FluentFormat("dialog-settings.language", checked=0, language=F["item"]),
        id=WIDGET_LANGUAGE_SELECT,
        items=list(PreferredLanguage),
        item_id_getter=str,
        type_factory=PreferredLanguage,
        # Default value is not supported, see `set_defaults`
    ),
    Checkbox(
        FluentFormat("dialog-settings.accept_uncompressed_checked"),
        FluentFormat("dialog-settings.accept_uncompressed_unchecked"),
        id=WIDGET_ACCEPT_UNCOMPRESSED,
        # Dynamic default value is not supported, see `set_defaults`
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


async def set_defaults(_, dialog_manager: DialogManager) -> None:
    user = cast(UserEntity, dialog_manager.middleware_data[USER_ENTITY_KEY])
    await cast(ManagedCheckbox, dialog_manager.find(WIDGET_ACCEPT_UNCOMPRESSED)).set_checked(user.accept_compressed)
    if user.preferred_language is not None:
        await cast(ManagedRadio[PreferredLanguage], dialog_manager.find(WIDGET_LANGUAGE_SELECT)).set_checked(
            user.preferred_language
        )


dialog = Dialog(
    start_window,
    on_start=set_defaults,
    name=__name__,
)
