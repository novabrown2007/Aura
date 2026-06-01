"""Weather forecast model for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.weather.models.weatherSource import WeatherSource


@dataclass(slots=True)
class WeatherForecast:
    """A multi-period weather forecast."""

    location: str = ""
    source: str = WeatherSource.UNKNOWN
    timestamp: str = ""
    hourly: list[dict[str, Any]] = field(default_factory=list)
    daily: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "source": WeatherSource.normalize(self.source),
            "timestamp": self.timestamp,
            "hourly": [dict(item) for item in self.hourly],
            "daily": [dict(item) for item in self.daily],
            "alerts": [dict(item) for item in self.alerts],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            location=str(values.get("location") or ""),
            source=WeatherSource.normalize(values.get("source")),
            timestamp=str(values.get("timestamp") or ""),
            hourly=[dict(item) for item in list(values.get("hourly") or [])],
            daily=[dict(item) for item in list(values.get("daily") or [])],
            alerts=[dict(item) for item in list(values.get("alerts") or [])],
            metadata=dict(values.get("metadata") or {}),
        )
