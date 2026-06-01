"""Forecast view model for Aura UI surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ForecastViewModel:
    """Compact UI model for hourly and daily forecasts."""

    location: str = ""
    hourly: list[dict[str, Any]] = field(default_factory=list)
    daily: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "hourly": [dict(item) for item in self.hourly],
            "daily": [dict(item) for item in self.daily],
            "alerts": [dict(item) for item in self.alerts],
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }
