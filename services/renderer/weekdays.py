from dataclasses import dataclass, field
from enum import IntEnum


_DEFAULT_NAMES = ["нл", "пн", "вт", "ср", "чт", "пт", "сб", "вс"]
class WeekDay(IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    def __str__(self) -> str:
        return _DEFAULT_NAMES[self.value].capitalize()


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
                tags = f"({','.join(entry.tags)}) " if entry.tags else ""
                line = f"{weekday} {entry.time} {tags}{entry.description}"
                lines.append(line)
        return "\n".join(lines)
