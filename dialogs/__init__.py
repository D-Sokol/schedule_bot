from .main_menu import dialog as main_menu_dialog
from .backgrounds import dialog as backgrounds_dialog
from .upload_background import dialog as upload_background_dialog
from .schedule_creation import dialog as schedule_creation_dialog
from .schedule_wizard import dialog as schedule_wizard_dialog
from .templates import dialog as templates_dialog
from .administration import dialog as admin_dialog
from .user_selection import dialog as user_selection_dialog

all_dialogs = [
    main_menu_dialog,
    backgrounds_dialog,
    upload_background_dialog,
    schedule_creation_dialog,
    schedule_wizard_dialog,
    templates_dialog,
    admin_dialog,
    user_selection_dialog,
]
