import logging
from typing import Optional

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import StartMode, ShowMode
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.kbd import Button, Start
from aiogram_dialog.widgets.kbd.button import OnClick


logger = logging.getLogger(__name__)


class StartWithData(Start):
    """
    This widget is similar to :class:`from aiogram_dialog.widgets.kbd.state.Start`,
    but re-uses start data from the current dialog instead of static data.
    If data keys are provided, only given keys are copied. If static data is provided,
    it takes priority over values from current context.
    """

    def __init__(
        self,
        text: Text,
        id: str,  # noqa
        state: State,
        data: dict | None = None,
        on_click: Optional[OnClick] = None,
        show_mode: Optional[ShowMode] = None,
        mode: StartMode = StartMode.NORMAL,
        when: WhenCondition = None,
        data_keys: list[str] | None = None,
        dialog_data_keys: list[str] | None = None,
    ):
        super().__init__(
            text=text,
            id=id,
            state=state,
            data=data,
            on_click=on_click,
            show_mode=show_mode,
            mode=mode,
            when=when,
        )
        self.data_keys = data_keys
        self.dialog_data_keys = dialog_data_keys

    async def _on_click(
        self,
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
    ):
        if self.user_on_click:
            await self.user_on_click(callback, self, manager)

        data = {}

        if isinstance(manager.start_data, dict):
            if self.data_keys is None:
                data.update(manager.start_data)
            else:
                data.update({key: manager.start_data.get(key) for key in self.data_keys})

        if isinstance(manager.dialog_data, dict):
            if self.dialog_data_keys is None:
                # Dialog data is usually large unlike start data, so default behaviour for them is different.
                pass
            else:
                data.update({key: manager.dialog_data.get(key) for key in self.dialog_data_keys})

        if self.start_data:
            data.update(self.start_data)

        await manager.start(
            state=self.state,
            data=data,
            mode=self.mode,
            show_mode=self.show_mode,
        )
