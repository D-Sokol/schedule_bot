from dataclasses import dataclass
from uuid import UUID

# Should be exactly the same, also app uses a pydantic validation.
from services.renderer import Template as TemplateEntity, Schedule as ScheduleEntity


@dataclass
class UserEntity:
    telegram_id: int
    is_admin: bool
    is_banned: bool


@dataclass
class ImageEntity:
    element_id: UUID
    name: str
    file_id_photo: str | None
    file_id_document: str | None


__all__ = [
    "UserEntity",
    "ImageEntity",
    "TemplateEntity",
    "ScheduleEntity",
]
