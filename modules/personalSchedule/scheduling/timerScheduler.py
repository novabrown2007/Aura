"""Timer helpers for Aura's unified personal schedule hub."""

from __future__ import annotations

from datetime import datetime, timedelta


class TimerScheduler:
    """Build deterministic timer timestamps."""

    @staticmethod
    def endTimeFromDuration(durationSeconds: int) -> str:
        duration = max(0, int(durationSeconds or 0))
        return (datetime.utcnow() + timedelta(seconds=duration)).isoformat(timespec="seconds")
