"""Timer model for Aura's unified schedule hub."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.personalSchedule.models.scheduleState import ScheduleState


@dataclass
class Timer:
    """Timer-specific view over a schedule item."""

    timerId: str = ""
    title: str = ""
    durationSeconds: int = 0
    remainingSeconds: int = 0
    paused: bool = False
    state: ScheduleState = ScheduleState.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return a serializable timer payload."""

        return {
            "timerId": self.timerId,
            "title": self.title,
            "durationSeconds": int(self.durationSeconds or 0),
            "remainingSeconds": int(self.remainingSeconds or 0),
            "paused": bool(self.paused),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "metadata": dict(self.metadata or {}),
        }
