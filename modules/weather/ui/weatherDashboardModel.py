"""Dashboard model for the weather module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WeatherDashboardModel:
    """Composite weather dashboard state."""

    current: dict[str, Any] = field(default_factory=dict)
    forecast: dict[str, Any] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    sensors: list[dict[str, Any]] = field(default_factory=list)
    thresholds: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    sourceSnapshot: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "current": dict(self.current),
            "forecast": dict(self.forecast),
            "alerts": [dict(item) for item in self.alerts],
            "sensors": [dict(item) for item in self.sensors],
            "thresholds": [dict(item) for item in self.thresholds],
            "locations": [dict(item) for item in self.locations],
            "sourceSnapshot": dict(self.sourceSnapshot),
        }
