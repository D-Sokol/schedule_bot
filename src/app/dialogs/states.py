from aiogram.filters.state import State, StatesGroup


class MainMenuStates(StatesGroup):
    START = State()


class BackgroundsStates(StatesGroup):
    START = State()
    SELECTED_IMAGE = State()
    CONFIRM_DELETE = State()
    RENAME = State()


class ScheduleStates(StatesGroup):
    START = State()
    EXPECT_TEXT = State()
    EXPECT_DATE = State()
    EXPECT_DATE_CALENDAR = State()
    FINISH = State()


class ScheduleWizardStates(StatesGroup):
    START = State()
    SELECT_DOW = State()
    SELECT_TIME = State()
    SELECT_TAGS = State()
    SELECT_DESC = State()


class UploadBackgroundStates(StatesGroup):
    START = State()
    UPLOADED_NOT_DOCUMENT = State()
    UPLOADED_BAD_DIMENSIONS = State()
    UPLOADED_EXPECT_NAME = State()
    UPLOAD_FAILED = State()


class TemplatesStates(StatesGroup):
    START = State()


class AdministrationStates(StatesGroup):
    START = State()


class UserSelectionStates(StatesGroup):
    START = State()


class SettingsStates(StatesGroup):
    START = State()
