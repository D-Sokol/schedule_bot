import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import TEXT, BIGINT, UUID, VARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(DeclarativeBase, AsyncAttrs):
    pass


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    last_schedule: Mapped[str] = mapped_column(TEXT(), nullable=True)
    elements: Mapped[list["ImageAsset"]] = relationship(
        'ImageAsset', back_populates='owner', cascade="all, delete-orphan"
    )


class ImageAsset(Base):
    __tablename__ = "elements"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="u_name_user"),
    )
    element_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BIGINT(), ForeignKey("users.tg_id"), nullable=True)
    name: Mapped[str] = mapped_column(VARCHAR(50))
    file_id_photo: Mapped[str | None] = mapped_column(VARCHAR(83), nullable=True)
    file_id_document: Mapped[str | None] = mapped_column(VARCHAR(71), nullable=True)

    owner: Mapped[User | None] = relationship(back_populates="elements")
