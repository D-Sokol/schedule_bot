import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date
from itertools import count
from typing import cast

import msgpack
from fluentogram import TranslatorRunner

from database_models import User, ImageAsset
from services.renderer import INPUT_SUBJECT_NAME, USER_ID_HEADER, ELEMENT_NAME_HEADER, START_DATE_HEADER
from services.renderer.templates import Template
from services.renderer.weekdays import WeekDay, Time, Entry, Schedule

from .database_mixin import DatabaseRegistryMixin
from .nats_mixin import NATSRegistryMixin

logger = logging.getLogger(__file__)


class ScheduleRegistryAbstract(ABC):
    _ENTRY_PATTERN = re.compile(
        r"""
            (\w+)\s+  # weekday: пн
            (\d{1,2}:\d{1,2})\s+  # time: 17:00
            (?:\((\w+)\)\s+)?  # tag in brackets: (platform1)
            (.*)  # The following is entry description 
        """,
        re.VERBOSE,
    )

    @abstractmethod
    def load_weekdays(self) -> dict[str, WeekDay]:
        raise NotImplementedError

    @abstractmethod
    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        raise NotImplementedError

    @abstractmethod
    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        raise NotImplementedError

    @abstractmethod
    async def render_schedule(
            self,
            user_id: int,
            chat_id: int,
            schedule: Schedule,
            background: ImageAsset,
            template: Template,
            start: date,
    ) -> None:
        raise NotImplementedError

    def parse_schedule_text(self, text: str) -> tuple[Schedule, list[str]]:
        schedule: dict[WeekDay, list[Entry]] = defaultdict(list)
        weekdays = self.load_weekdays()
        unparsed = []
        for line in text.splitlines():
            line = line.strip().replace('\u2068', '')  # fluent things
            if not line:
                continue
            match = self._ENTRY_PATTERN.fullmatch(line)
            if match is None:
                unparsed.append(line)
                continue
            weekday_str, time_str, tags_str, desc = cast(tuple[str | None, ...], match.groups())
            assert weekday_str is not None and time_str is not None and desc is not None, "Bad regexp"
            weekday = weekdays.get(weekday_str.lower())

            if weekday is None:
                # To ensure storing last schedule in DB for any locale,
                # we also use "1", "2", ... keys (unconditionally) for weekdays.
                try:
                    weekday = WeekDay(int(weekday_str))
                except ValueError:
                    unparsed.append(line)
                    continue
            # Note: int("09") == 9
            h, m = map(int, time_str.split(":"))
            entry = Entry(
                time=Time(hour=h, minute=m), description=desc, tags=set(tags_str.split(",") if tags_str else ())
            )
            schedule[weekday].append(entry)

        for entries in schedule.values():
            entries.sort(key=lambda e: (e.time.hour, e.time.minute))
        return Schedule(records=dict(schedule)), unparsed

    @classmethod
    def dump_schedule_text(cls, schedule: Schedule) -> str:
        lines = []
        for weekday in WeekDay:
            entries = schedule.records.get(weekday)
            if not entries:
                continue
            for entry in entries:
                tags = f"({','.join(entry.tags)}) " if entry.tags else ""
                line = f"{weekday.value} {entry.time} {tags}{entry.description}"
                lines.append(line)
        return "\n".join(lines)


class MockScheduleRegistry(ScheduleRegistryAbstract):
    def load_weekdays(self) -> dict[str, WeekDay]:
        _WEEKDAY_BY_NAMES: dict[str, WeekDay] = {
            "пн": WeekDay.MONDAY,
            "вт": WeekDay.TUESDAY,
            "ср": WeekDay.WEDNESDAY,
            "чт": WeekDay.THURSDAY,
            "пт": WeekDay.FRIDAY,
            "сб": WeekDay.SATURDAY,
            "вс": WeekDay.SUNDAY,
        }
        _WEEKDAY_BY_ALIAS: dict[str, WeekDay] = {
            "понедельник": WeekDay.MONDAY,
            "вторник": WeekDay.TUESDAY,
            "среда": WeekDay.WEDNESDAY,
            "четверг": WeekDay.THURSDAY,
            "пятница": WeekDay.FRIDAY,
            "суббота": WeekDay.SATURDAY,
            "субкота": WeekDay.SATURDAY,  # noqa
            "воскресенье": WeekDay.SUNDAY,
        }

        _WEEKDAY_BY_ALL_NAMES: dict[str, WeekDay] = {**_WEEKDAY_BY_NAMES, **_WEEKDAY_BY_ALIAS}
        assert all(s.islower() for s in _WEEKDAY_BY_ALL_NAMES)
        return _WEEKDAY_BY_ALL_NAMES

    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        if user_id is not None:
            return None
        return Schedule(
            records={
                WeekDay.TUESDAY: [
                    Entry(time=Time(hour=11, minute=0), description="Спортзал"),
                    Entry(time=Time(hour=17, minute=30), description="Отдых"),
                ],
                WeekDay.FRIDAY: [
                    Entry(time=Time(hour=11, minute=0), description="Неторопливая прогулка по парку"),
                ],
            }
        )

    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        logger.info("Saving schedule for user %s:\n%s", user_id, schedule)

    async def render_schedule(
            self,
            user_id: int,
            chat_id: int,
            schedule: Schedule,
            background: ImageAsset,
            template: Template,
            start: date,
    ) -> None:
        pass


class DbScheduleRegistry(ScheduleRegistryAbstract, DatabaseRegistryMixin, NATSRegistryMixin):
    def __init__(self, i18n: TranslatorRunner, **kwargs):
        super().__init__(**kwargs)
        self.i18n = i18n

    def load_weekdays(self) -> dict[str, WeekDay]:
        result: dict[str, WeekDay] = {}
        for wd in WeekDay:
            key = self.i18n.get(f"weekdays-d{wd.value}").lower()
            result[key] = wd
            for i in count(start=1):
                key = self.i18n.get(f"weekdays-d{wd.value}.alias{i}")
                if key is None:
                    break
                result[key.lower()] = wd
        return result

    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        if user_id is None:
            return None
        user: User | None = await self.session.get(User, user_id)
        if user is None or (last_schedule := user.last_schedule) is None:
            return None
        schedule, unparsed = self.parse_schedule_text(last_schedule)
        assert not unparsed, "Mismatch between last schedule saving and parsing"
        return schedule

    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        logger.info("Saving schedule for user %s", user_id)
        if user_id is None:
            logger.error("Cannot save schedule in global scope!")
            return
        user: User | None = await self.session.get(User, user_id)
        if user is None:
            logger.error("Cannot save schedule for unknown user id %d", user_id)
            return

        user.last_schedule = self.dump_schedule_text(schedule)
        self.session.add(user)
        await self.session.commit()

    async def render_schedule(
            self,
            user_id: int,
            chat_id: int,
            schedule: Schedule,
            background: ImageAsset,
            template: Template,
            start: date,
    ) -> None:
        payload: bytes = msgpack.packb([
            template.model_dump(by_alias=True, mode="json"),
            schedule.model_dump(by_alias=True, mode="json"),
        ])

        await self.js.publish(
            subject=INPUT_SUBJECT_NAME,
            payload=payload,
            headers={
                USER_ID_HEADER: str(user_id),
                ELEMENT_NAME_HEADER: f"{user_id}.{background.element_id}",
                START_DATE_HEADER: start.isoformat(),
            },
        )
