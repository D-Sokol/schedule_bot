from sqlalchemy import ForeignKey, String, Text, BigInteger, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(DeclarativeBase, AsyncAttrs):
    pass


class User(Base):
    __tablename__ = "users"
    tg_id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    last_schedule: Mapped[str] = mapped_column(Text(), nullable=True)
    elements = relationship('ImageAsset', backref='owner')


class ImageAsset(Base):
    __tablename__ = "elements"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="u_name_user"),
    )
    element_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger(), ForeignKey("users.tg_id"), nullable=True)
    name: Mapped[str] = mapped_column(String(50))
    file_id_photo: Mapped[str | None] = mapped_column(String(83), nullable=True)
    file_id_document: Mapped[str | None] = mapped_column(String(71), nullable=True)
