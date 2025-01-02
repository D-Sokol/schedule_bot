import asyncio
import io
from abc import ABC, abstractmethod
from datetime import date, timedelta
from functools import lru_cache
from typing import Annotated, Any, Literal

from PIL import Image, ImageColor, ImageDraw, ImageFont
from nats.js.errors import ObjectNotFoundError
from nats.js.object_store import ObjectStore
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from .weekdays import WeekDay, Entry, Schedule

WEEK_LENGTH = len(WeekDay)


@lru_cache(maxsize=64)
def load_font(font_name: str, font_size: int = 72) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_name, size=font_size)


class TemplateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BasePatch(TemplateModel, ABC):
    type: str

    @abstractmethod
    async def apply(self, image: Image.Image, draw: ImageDraw.ImageDraw, format_args: dict[str, Any], **kwargs) -> None:
        raise NotImplementedError


class BasePositionedPatch(BasePatch, ABC):
    xy: tuple[int, int]
    required_tag: str | None = Field(default=None, alias="tag")

    def is_visible(self, tags: set[str] | None = None) -> bool:
        if self.required_tag is None:
            return True
        if tags is None:
            return False
        return self.required_tag in tags


class TextPatch(BasePositionedPatch):
    type: Literal["text"] = "text"

    template: str = Field(alias="text", description="f-string template for this patch")
    fill: str = Field(alias="color")
    # See https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors for anchors
    anchor: str = Field(default="la", pattern=r"[lmr][amsbd]")
    font_size: int = 28
    font_name: str = "Arial.ttf"
    stroke_width: int = 0
    stroke_fill: str | None = Field(default=None, alias="stroke_color")

    _font: ImageFont.FreeTypeFont

    async def apply(self, image: Image.Image, draw: ImageDraw.ImageDraw, format_args: dict[str, Any], **kwargs) -> None:
        draw.multiline_text(
            xy=self.xy,
            text=self.template.format(**format_args),
            fill=self.fill,
            font=self._font,
            anchor=self.anchor,
            stroke_width=self.stroke_width,
            stroke_fill=self.stroke_fill,
        )

    def model_post_init(self, __context: Any) -> None:
        _ = ImageColor.getrgb(self.fill)
        if self.stroke_fill is not None:
            _ = ImageColor.getrgb(self.stroke_fill)
        self._font = load_font(self.font_name, self.font_size)


class ImagePatch(BasePositionedPatch):
    type: Literal["image"] = "image"

    name: str | None = None
    element_id: str | None = None

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.name is None and self.element_id is None:
            raise ValueError("Either name or element id is required")

    async def _get_patch(self, store: ObjectStore | None = None, session: AsyncSession | None = None) -> Image.Image:
        if store is None:
            raise ValueError("Cannot get patch without store")

        if self.element_id is not None:
            element_id: str = f"0.{self.element_id}"
        else:
            assert self.name is not None
            result = await session.execute(
                text("SELECT element_id FROM elements WHERE user_id IS NULL AND name = :name LIMIT 1"),
                {"name": self.name},
            )
            element_uuid: UUID | None = result.scalar()
            print(element_uuid, type(element_uuid))
            if element_uuid is None:
                raise ValueError(f"Unknown image name {self.name}")
            element_id = f"0.{element_uuid}"

        try:
            result = await store.get(element_id)
        except ObjectNotFoundError as e:
            raise ValueError(f"Missing element {element_id} ({self.name=})") from e
        stream = io.BytesIO(result.data)
        return Image.open(stream).convert(mode="RGBA")

    async def apply(
            self,
            image: Image.Image,
            draw: ImageDraw.ImageDraw,
            format_args: dict[str, Any],
            store: ObjectStore | None = None,
            session: AsyncSession | None = None,
            **kwargs
    ) -> None:
        patch = await self._get_patch(store, session)
        mask = patch.getchannel("A")
        image.paste(patch, self.xy, mask=mask)


class PatchSet(BasePatch):
    type: Literal["set"] = "set"
    patches: list[Annotated[TextPatch | ImagePatch, Field(discriminator="type")]] = Field(default_factory=list)

    async def apply(
            self,
            image: Image.Image,
            draw: ImageDraw.ImageDraw,
            format_args: dict[str, Any],
            tags: set[str] | None = None,
            **kwargs
    ) -> None:
        await asyncio.gather(
            *(
                patch.apply(image, draw, format_args, **kwargs)
                for patch in self.patches
                if patch.is_visible(tags)
            )
        )

    @model_validator(mode="before")
    @classmethod
    def _wrap_list(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"patches": data}
        return data


class DayPatch(TemplateModel):
    type: Literal["day"] = "day"

    always: PatchSet = Field(default_factory=PatchSet)
    if_none: PatchSet = Field(default_factory=PatchSet)
    record_patches: list[PatchSet] = Field(default_factory=list)

    async def apply(
            self,
            image: Image.Image,
            draw: ImageDraw.ImageDraw,
            format_args: dict[str, Any],
            entries: list[Entry],
            **kwargs
    ) -> None:
        await self.always.apply(image, draw, format_args, **kwargs)
        for entry, record_patch in zip(entries, self.record_patches):
            format_args["entry"] = entry
            await record_patch.apply(image, draw, format_args, tags=entry.tags, **kwargs)
        if not entries:
            await self.if_none.apply(image, draw, format_args, **kwargs)


class Template(TemplateModel):
    always: PatchSet = Field(default_factory=PatchSet)
    patches: dict[WeekDay, DayPatch] = Field(default_factory=dict)

    width: int = 1344
    height: int = 768

    async def apply(
            self,
            image: Image.Image,
            draw: ImageDraw.ImageDraw,
            start_date: date,
            schedule: Schedule,
            store: ObjectStore | None = None,
            session: AsyncSession | None = None,
    ):
        format_args: dict[str, Any] = {
            "start": start_date,
            "end": start_date + timedelta(days=WEEK_LENGTH - 1),
            **{
                f"day{i + 1}": start_date + timedelta(days=i) for i in range(WEEK_LENGTH)
            },
        }
        await self.always.apply(image, draw, format_args, store=store, session=session)

        for i, weekday in enumerate(WeekDay):
            day_patch = self.patches.get(weekday)
            if day_patch is None:
                continue
            records: list[Entry] = schedule.records.get(weekday) or []
            format_args["date"] = start_date + timedelta(days=i)
            await day_patch.apply(image, draw, format_args, records, store=store, session=session)