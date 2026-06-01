"""Weather source identifiers for Aura."""

from __future__ import annotations


class WeatherSource:
    """Canonical source labels for weather data."""

    LOCAL_SENSOR = "LOCAL_SENSOR"
    WEATHER_API = "WEATHER_API"
    CACHED_API = "CACHED_API"
    SIMULATED = "SIMULATED"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def normalize(cls, value) -> str:
        """Return a canonical weather source label."""

        text = str(value or cls.UNKNOWN).strip().upper().replace(" ", "_").replace("-", "_")
        return text if text in {
            cls.LOCAL_SENSOR,
            cls.WEATHER_API,
            cls.CACHED_API,
            cls.SIMULATED,
            cls.UNKNOWN,
        } else cls.UNKNOWN
