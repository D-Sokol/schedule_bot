import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery

from database_models import User

logger = logging.getLogger(__name__)


class BlacklistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User = data.get("user")
        if user and user.is_banned:
            logger.info("Update from user %d ignored due to blacklist", user.tg_id)
            if isinstance(event, CallbackQuery):
                # CallbackQuery should be answered to avoid lagging animation on user side.
                await event.answer()
            return

        return await handler(event, data)
