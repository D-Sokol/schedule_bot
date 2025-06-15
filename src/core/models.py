from dataclasses import dataclass
from uuid import UUID

# Should be exactly the same, also app uses a pydantic validation.
from services.renderer import Template as TemplateModel, Schedule as ScheduleModel


@dataclass
class UserModel:
    telegram_id: int
    is_admin: bool
    is_banned: bool


@dataclass
class ImageModel:
    element_id: UUID
    name: str
    file_id_photo: str | None
    file_id_document: str | None


__all__ = [
    "UserModel",
    "ImageModel",
    "TemplateModel",
    "ScheduleModel",
]
