"""Current weather model for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.weather.models.weatherSource import WeatherSource


@dataclass(slots=True)
class WeatherData:
    """A normalized current weather reading."""

    location: str = ""
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    windSpeed: float | None = None
    windDirection: str = ""
    condition: str = ""
    visibility: float | None = None
    uvIndex: float | None = None
    feelsLike: float | None = None
    source: str = WeatherSource.UNKNOWN
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "windSpeed": self.windSpeed,
            "windDirection": self.windDirection,
            "condition": self.condition,
            "visibility": self.visibility,
            "uvIndex": self.uvIndex,
            "feelsLike": self.feelsLike,
            "source": WeatherSource.normalize(self.source),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            location=str(values.get("location") or values.get("name") or ""),
            temperature=values.get("temperature", values.get("temperatureC")),
            humidity=values.get("humidity", values.get("humidityPercent")),
            pressure=values.get("pressure"),
            windSpeed=values.get("windSpeed", values.get("wind_speed")),
            windDirection=str(values.get("windDirection") or values.get("wind_direction") or ""),
            condition=str(values.get("condition") or values.get("weather") or ""),
            visibility=values.get("visibility"),
            uvIndex=values.get("uvIndex", values.get("uv_index")),
            feelsLike=values.get("feelsLike", values.get("feels_like")),
            source=WeatherSource.normalize(values.get("source")),
            timestamp=str(values.get("timestamp") or values.get("observedAt") or values.get("updatedAt") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
