from abc import ABC, abstractmethod
from datetime import date, timedelta
from functools import lru_cache
from typing import Annotated, Any, Literal

from PIL import ImageColor, ImageDraw, ImageFont
from pydantic import BaseModel, Field

from .weekdays import WeekDay, Entry, Schedule

WEEK_LENGTH = len(WeekDay)


@lru_cache(maxsize=64)
def load_font(font_name: str, font_size: int = 72) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_name, size=font_size)


class TemplateModel(BaseModel):
    pass


class BasePatch(TemplateModel, ABC):
    type: str

    @abstractmethod
    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any]) -> None:
        raise NotImplementedError


class BasePositionedPatch(BasePatch, ABC):
    xy: tuple[int, int]


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

    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any]) -> None:
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

    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any]) -> None:
        raise NotImplementedError


class PatchSet(BasePatch):
    type: Literal["set"] = "set"
    patches: list[Annotated[TextPatch | ImagePatch, Field(discriminator="type")]] = Field(default_factory=list)

    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any]) -> None:
        for patch in self.patches:
            patch.apply(draw, format_args)


class DayPatch(TemplateModel):
    type: Literal["day"] = "day"

    always: PatchSet = Field(default_factory=PatchSet)
    if_none: PatchSet = Field(default_factory=PatchSet)
    record_patches: list[PatchSet] = Field(default_factory=list)

    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any], entries: list[Entry]) -> None:
        self.always.apply(draw, format_args)
        for entry, record_patch in zip(entries, self.record_patches):
            format_args["entry"] = entry
            record_patch.apply(draw, format_args)
        if not entries:
            self.if_none.apply(draw, format_args)


class Template(TemplateModel):
    always: PatchSet = Field(default_factory=PatchSet)
    day1: DayPatch = Field(default_factory=DayPatch)
    day2: DayPatch = Field(default_factory=DayPatch)
    day3: DayPatch = Field(default_factory=DayPatch)
    day4: DayPatch = Field(default_factory=DayPatch)
    day5: DayPatch = Field(default_factory=DayPatch)
    day6: DayPatch = Field(default_factory=DayPatch)
    day7: DayPatch = Field(default_factory=DayPatch)

    def get_days_list(self) -> list[DayPatch]:
        return [self.day1, self.day2, self.day3, self.day4, self.day5, self.day6, self.day7]

    def apply(self, draw: ImageDraw.ImageDraw, start_date: date, schedule: Schedule):
        format_args: dict[str, Any] = {
            "start": start_date,
            "end": start_date + timedelta(days=WEEK_LENGTH - 1),
            **{
                f"day{i + 1}": start_date + timedelta(days=i) for i in range(WEEK_LENGTH)
            },
        }
        self.always.apply(draw, format_args)

        for i, day_patch in enumerate(self.get_days_list()):
            records: list[Entry] = schedule.records.get(WeekDay(i + 1)) or []
            format_args["date"] = start_date + timedelta(days=i)
            day_patch.apply(draw, format_args, records)
