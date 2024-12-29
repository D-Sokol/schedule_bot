"""
This script renders a final schedule as a separate microservice to avoid lags in bot responses.
"""
import asyncio
import io
import json
import logging
import os
from abc import ABC, abstractmethod
from asyncio import Event
from datetime import date, timedelta
from functools import partial, lru_cache
from typing import Annotated, Any, Literal

import nats
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.object_store import ObjectStore
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

BUCKET_NAME = "assets"
INPUT_SUBJECT_NAME = "schedules.request"
OUTPUT_SUBJECT_NAME = "schedules.ready"
IMAGE_FORMAT = "png"

USER_ID_HEADER = "Sch-User-Id"
CHAT_ID_HEADER = "Sch-Chat-Id"
ELEMENT_NAME_HEADER = "Sch-Element-Name"

logger = logging.getLogger(__name__)


WEEK_LENGTH = 7


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

    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any]) -> None:
        font = load_font(self.font_name, self.font_size)
        draw.multiline_text(
            xy=self.xy,
            text=self.template.format(**format_args),
            fill=self.fill,
            font=font,
            anchor=self.anchor,  # TODO: stroke_width, stroke_fill = (0, None)
        )


class ImagePatch(BasePositionedPatch):
    type: Literal["image"] = "image"

    name: str

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

    def apply(self, draw: ImageDraw.ImageDraw, format_args: dict[str, Any], entries: list[str]) -> None:
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

    def apply(self, draw: ImageDraw.ImageDraw, start_date: date, schedule: list[list[str]]):  # TODO: schedule type
        format_args: dict[str, Any] = {
            "start": start_date,
            "end": start_date + timedelta(days=WEEK_LENGTH - 1),
            **{
                f"day{i + 1}": start_date + timedelta(days=i) for i in range(WEEK_LENGTH)
            },
        }
        self.always.apply(draw, format_args)
        for i, (day_patch, records) in enumerate(zip(self.get_days_list(), schedule)):
            format_args["date"] = start_date + timedelta(days=i)
            day_patch.apply(draw, format_args, records)


async def render(msg: Msg, js: JetStreamContext, store: ObjectStore):
    if msg.headers is None:
        logger.error("Got message without headers")
        raise ValueError("Headers are required for message processing")

    user_id = msg.headers[USER_ID_HEADER]
    chat_id = msg.headers[CHAT_ID_HEADER]
    element_name = msg.headers[ELEMENT_NAME_HEADER]

    payload = json.loads(msg.data.decode())

    logger.info("Converting %s for %s with payload %s", element_name, user_id, payload)
    background_data = await store.get(element_name)
    if background_data.data is None:
        logger.error("No content in image %s.%s", user_id, element_name)
        raise ValueError("No content in image")
    background = Image.open(io.BytesIO(background_data.data), formats=[IMAGE_FORMAT])

    # TODO: edit wrt template
    stream = io.BytesIO()
    background.save(stream, format=IMAGE_FORMAT)

    logging.debug("Created schedule for %s", user_id)
    await js.publish(
        subject=OUTPUT_SUBJECT_NAME,
        payload=stream.getvalue(),
        headers={
            USER_ID_HEADER: user_id,
            CHAT_ID_HEADER: chat_id,
        },
    )
    await msg.ack()


async def render_loop(js: JetStreamContext, shutdown_event: asyncio.Event | None = None):
    store = await js.object_store(BUCKET_NAME)
    await js.subscribe(INPUT_SUBJECT_NAME, cb=partial(render, js=js, store=store), durable="renderer", manual_ack=True)
    logger.info("Connected to NATS")

    if shutdown_event is None:
        shutdown_event = Event()

    try:
        assert shutdown_event is not None
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.debug("Main task was cancelled")
    logger.warning("Exiting main task")


async def main(servers: str = "nats://localhost:4222"):
    nc = await nats.connect(servers=servers)
    js = nc.jetstream()
    await render_loop(js)
    await nc.close()


if __name__ == '__main__':
    nats_servers_ = os.getenv("NATS_SERVERS")
    if nats_servers_ is None:
        logger.critical("Cannot run without nats url")
        exit(1)
    asyncio.run(main(nats_servers_))
