from aiogram.types import KeyboardButton, KeyboardButtonRequestUsers
from aiogram_dialog.api.internal import RawKeyboard
from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram_dialog.widgets.text import Text


class RequestUsers(Keyboard):
    def __init__(
        self,
        text: Text,
        max_quantity: int = 1,
        request_id: int = 1,
        user_is_bot: bool | None = None,
        user_is_premium: bool | None = None,
        request_name: bool = None,
        request_username: bool | None = None,
        request_photo: bool | None = None,
        when: WhenCondition = None,
    ):
        super().__init__(when=when)
        self.text = text
        self.request = KeyboardButtonRequestUsers(
            request_id=request_id,
            max_quantity=max_quantity,
            user_is_bot=user_is_bot,
            user_is_premium=user_is_premium,
            request_name=request_name,
            request_username=request_username,
            request_photo=request_photo,
        )

    async def _render_keyboard(
        self,
        data: dict,
        manager: DialogManager,
    ) -> RawKeyboard:
        return [
            [
                KeyboardButton(
                    text=await self.text.render_text(data, manager),
                    request_users=self.request,
                ),
            ],
        ]
