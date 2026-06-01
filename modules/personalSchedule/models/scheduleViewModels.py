"""View models for Aura's personal schedule UI surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScheduleViewModel:
    title: str = ""
    summary: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)

    def asDict(self) -> dict[str, Any]:
        return {"title": self.title, "summary": self.summary, "items": list(self.items)}


@dataclass
class CalendarViewModel:
    view: str = "day"
    day: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)

    def asDict(self) -> dict[str, Any]:
        return {"view": self.view, "day": self.day, "items": list(self.items)}


@dataclass
class UpcomingEventsModel:
    items: list[dict[str, Any]] = field(default_factory=list)

    def asDict(self) -> dict[str, Any]:
        return {"items": list(self.items)}
