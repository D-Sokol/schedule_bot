import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import *


logger = logging.getLogger(__file__)


class WeekDay(Enum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


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


@dataclass
class Schedule:
    records: Dict[WeekDay, list[Entry]]

    def __str__(self) -> str:
        lines = []
        for weekday in WeekDay:
            entries = self.records.get(weekday)
            if not entries:
                continue
            for entry in entries:
                # TODO: better weekday representation
                line = f"{weekday.name} {entry.time} {entry.description}"
                lines.append(line)
        return "\n".join(lines)


class ScheduleRegistryAbstract(ABC):
    @abstractmethod
    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        raise NotImplementedError

    @abstractmethod
    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        raise NotImplementedError

    def parse_schedule_text(self, text: str) -> Schedule:
        raise NotImplementedError  # TODO


class MockScheduleRegistry(ScheduleRegistryAbstract):
    async def get_last_schedule(self, user_id: int | None) -> Schedule | None:
        return None

    async def update_last_schedule(self, user_id: int | None, schedule: Schedule) -> None:
        pass
