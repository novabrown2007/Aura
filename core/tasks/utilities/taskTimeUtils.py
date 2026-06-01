"""Time helpers for Aura task orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta


class TaskTimeUtils:
    """Shared datetime helpers for scheduling."""

    @staticmethod
    def utcNow() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def toIso(value: datetime | None = None) -> str:
        return (value or datetime.utcnow()).isoformat(timespec="seconds")

    @staticmethod
    def parse(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    @staticmethod
    def addSeconds(value: datetime | None, seconds: float) -> datetime:
        return (value or datetime.utcnow()) + timedelta(seconds=float(seconds))

    @staticmethod
    def isDue(runAt: str | None, now: datetime | None = None) -> bool:
        runTime = TaskTimeUtils.parse(runAt)
        if runTime is None:
            return False
        return runTime <= (now or datetime.utcnow())
