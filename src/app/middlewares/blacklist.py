import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app.middlewares.db_session import USER_ENTITY_KEY
from core.entities import UserEntity

logger = logging.getLogger(__name__)


class BlacklistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: UserEntity = data.get(USER_ENTITY_KEY)
        if user and user.is_banned:
            logger.info("Update from user %d ignored due to blacklist", user.telegram_id)
            if isinstance(event, CallbackQuery):
                # CallbackQuery should be answered to avoid lagging animation on user side.
                await event.answer()
            return None

        return await handler(event, data)
