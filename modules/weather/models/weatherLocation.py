"""Weather location model for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WeatherLocation:
    """A named location used by the weather module."""

    locationId: str = ""
    name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    isHome: bool = False
    isFavorite: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "locationId": self.locationId,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "isHome": bool(self.isHome),
            "isFavorite": bool(self.isFavorite),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            locationId=str(values.get("locationId") or values.get("location_id") or ""),
            name=str(values.get("name") or values.get("label") or ""),
            latitude=values.get("latitude"),
            longitude=values.get("longitude"),
            isHome=bool(values.get("isHome", values.get("is_home", False))),
            isFavorite=bool(values.get("isFavorite", values.get("is_favorite", False))),
            metadata=dict(values.get("metadata") or {}),
        )
