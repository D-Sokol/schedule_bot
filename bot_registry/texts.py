import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import cast


logger = logging.getLogger(__file__)


class WeekDay(Enum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    def __str__(self) -> str:
        return _WEEKDAY_NAMES[self].capitalize()


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
_WEEKDAY_NAMES: dict[WeekDay, str] = {wd: name for name, wd in _WEEKDAY_BY_NAMES.items()}
assert 7 == len(_WEEKDAY_NAMES) == len(WeekDay)


@dataclass
class Time:
    hour: int
    minute: int = 0

    def __str__(self) -> str:
        return f"{self.hour}:{self.minute:02d}"


@dataclass
class Entry:
    time: Time
    description: str
    tags: set[str] = field(default_factory=set)


@dataclass
class Schedule:
    records: dict[WeekDay, list[Entry]]

    def is_empty(self) -> bool:
        return all(not v for v in self.records.values())

    def __str__(self) -> str:
        lines = []
        for weekday in WeekDay:
            entries = self.records.get(weekday)
            if not entries:
                continue
            for entry in entries:
                line = f"{weekday} {entry.time} {entry.description}"
                lines.append(line)
        return "\n".join(lines)


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
    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        raise NotImplementedError

    @abstractmethod
    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        raise NotImplementedError

    @classmethod
    def parse_schedule_text(cls, text: str) -> tuple[Schedule, list[str]]:
        schedule: dict[WeekDay, list[Entry]] = defaultdict(list)
        unparsed = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            match = cls._ENTRY_PATTERN.fullmatch(line)
            if match is None:
                unparsed.append(line)
                continue
            weekday_str, time_str, tags_str, desc = cast(tuple[str | None, ...], match.groups())
            weekday = _WEEKDAY_BY_ALL_NAMES.get(weekday_str.lower())
            if weekday is None:
                unparsed.append(line)
                continue
            # Note: int("09") == 9
            h, m = map(int, time_str.split(":"))
            entry = Entry(time=Time(h, m), description=desc, tags=set(tags_str.split(",") if tags_str else ()))
            schedule[weekday].append(entry)

        for entries in schedule.values():
            entries.sort(key=lambda e: (e.time.hour, e.time.minute))
        return Schedule(records=dict(schedule)), unparsed


class MockScheduleRegistry(ScheduleRegistryAbstract):
    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        if user_id is not None:
            return None
        return Schedule(
            {
                WeekDay.TUESDAY: [Entry(Time(11, 0), "Спортзал"), Entry(Time(17, 30), "Отдых")],
                WeekDay.FRIDAY: [Entry(Time(11, 0), "Неторопливая прогулка по парку")]
            }
        )

    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        logger.info("Saving schedule for user %s:\n%s", user_id, schedule)
