import uuid
from typing import Optional, Sequence, cast

from sqlalchemy import Enum as ORMEnum
from sqlalchemy import ForeignKey, UniqueConstraint, func, select, text
from sqlalchemy.dialects.postgresql import BIGINT, TEXT, UUID, VARCHAR
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.entities import PreferredLanguage


class Base(DeclarativeBase, AsyncAttrs):
    pass


class UserModel(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_banned: Mapped[bool] = mapped_column(default=False, server_default="false")
    last_schedule: Mapped[str | None] = mapped_column(TEXT(), nullable=True)
    user_template: Mapped[str | None] = mapped_column(TEXT(), nullable=True)

    elements: Mapped[list["ImageElementModel"]] = relationship(
        "ImageElementModel", back_populates="owner", cascade="all, delete-orphan", lazy="raise"
    )
    settings: Mapped[Optional["UserSettingsModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="joined"
    )


class UserSettingsModel(Base):
    __tablename__ = "settings"
    tg_id: Mapped[int] = mapped_column(BIGINT(), ForeignKey("users.tg_id", ondelete="CASCADE"), primary_key=True)
    preferred_lang: Mapped[PreferredLanguage | None] = mapped_column(ORMEnum(PreferredLanguage), nullable=True)
    accept_compressed: Mapped[bool] = mapped_column(default=False, server_default="false")

    user: Mapped[UserModel] = relationship(back_populates="settings", single_parent=True, lazy="raise")


def _next_display_order(context: DefaultExecutionContext) -> int:
    owner_id = context.get_current_parameters().get("user_id")
    cursor = context.root_connection.execute(
        select(func.max(ImageElementModel.display_order) + text("1")).where(ImageElementModel.user_id == owner_id)
    )
    (display_order,) = cast(Sequence[int | None], cursor.fetchone())
    return display_order or 0


class ImageElementModel(Base):
    __tablename__ = "elements"
    __table_args__ = (UniqueConstraint("user_id", "name", name="u_name_user"),)
    element_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BIGINT(), ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(VARCHAR(50))
    file_id_photo: Mapped[str | None] = mapped_column(VARCHAR(90), nullable=True)
    file_id_document: Mapped[str | None] = mapped_column(VARCHAR(90), nullable=True)
    display_order: Mapped[int] = mapped_column(default=_next_display_order, nullable=False)

    owner: Mapped[UserModel | None] = relationship(back_populates="elements")
