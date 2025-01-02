import uuid
from typing import Sequence, cast

from sqlalchemy import ForeignKey, UniqueConstraint, select, text, func
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.dialects.postgresql import TEXT, BIGINT, UUID, VARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(DeclarativeBase, AsyncAttrs):
    pass


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    last_schedule: Mapped[str | None] = mapped_column(TEXT(), nullable=True)
    user_template: Mapped[str | None] = mapped_column(TEXT(), nullable=True)
    elements: Mapped[list["ImageAsset"]] = relationship(
        'ImageAsset', back_populates='owner', cascade="all, delete-orphan", lazy="raise"
    )


def _next_display_order(context: DefaultExecutionContext) -> int:
    owner_id = context.get_current_parameters().get("user_id")
    cursor = context.root_connection.execute(
        select(func.max(ImageAsset.display_order) + text("1")).where(ImageAsset.user_id == owner_id)
    )
    display_order, = cast(Sequence[int], cursor.fetchone())
    return display_order or 0


class ImageAsset(Base):
    __tablename__ = "elements"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="u_name_user"),
    )
    element_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BIGINT(), ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(VARCHAR(50))
    file_id_photo: Mapped[str | None] = mapped_column(VARCHAR(90), nullable=True)
    file_id_document: Mapped[str | None] = mapped_column(VARCHAR(90), nullable=True)
    display_order: Mapped[int] = mapped_column(default=_next_display_order, nullable=False)

    owner: Mapped[User | None] = relationship(back_populates="elements")
