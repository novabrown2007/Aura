"""Weather view model for Aura UI surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WeatherViewModel:
    """Compact UI model for current weather."""

    location: str = ""
    current: dict[str, Any] = field(default_factory=dict)
    indoorTemperature: float | None = None
    source: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "current": dict(self.current),
            "indoorTemperature": self.indoorTemperature,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }
