"""Weather cache coordination for Aura."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from modules.weather.models import WeatherData, WeatherForecast, WeatherSource


class WeatherCacheManager:
    """Manage cached weather data backed by SQLite."""

    def __init__(self, context=None, store=None, ttlMinutes: int = 15):
        self.context = context
        self.store = store
        self.ttlMinutes = int(ttlMinutes)
        self.logger = context.logger.getChild("Weather.Cache") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Cache") if getattr(context, "logger", None) else None
        return self

    def getCurrentWeather(self, location: str) -> WeatherData | None:
        row = self._get(self._cacheKey("current", location))
        return None if row is None else WeatherData.fromDict(row)

    def setCurrentWeather(self, weatherData: WeatherData):
        self._set("current", weatherData.location, weatherData.asDict(), weatherData.source or WeatherSource.WEATHER_API)

    def getHourlyForecast(self, location: str, hours: int = 24) -> WeatherForecast | None:
        row = self._get(self._cacheKey("hourly", location, hours))
        return None if row is None else WeatherForecast.fromDict(row)

    def setHourlyForecast(self, forecast: WeatherForecast, hours: int = 24):
        self._set("hourly", forecast.location, forecast.asDict(), forecast.source or WeatherSource.WEATHER_API, suffix=str(int(hours)))

    def getWeeklyForecast(self, location: str, days: int = 7) -> WeatherForecast | None:
        row = self._get(self._cacheKey("weekly", location, days))
        return None if row is None else WeatherForecast.fromDict(row)

    def setWeeklyForecast(self, forecast: WeatherForecast, days: int = 7):
        self._set("weekly", forecast.location, forecast.asDict(), forecast.source or WeatherSource.WEATHER_API, suffix=str(int(days)))

    def getAlerts(self, location: str) -> list[dict[str, Any]]:
        row = self._get(self._cacheKey("alerts", location))
        if row is None:
            return []
        return list(row.get("alerts") or [])

    def setAlerts(self, location: str, alerts: list[dict[str, Any]]):
        payload = {"location": location, "alerts": [dict(alert) for alert in alerts]}
        self._set("alerts", location, payload, WeatherSource.WEATHER_API)

    def snapshot(self) -> dict[str, Any]:
        return {"ttlMinutes": self.ttlMinutes, "cache": list(self.store.listCache() if self.store else [])}

    def _set(self, itemType: str, location: str, payload: dict[str, Any], source: str, suffix: str = ""):
        if self.store is None:
            return
        self.store.upsertCache(
            self._cacheKey(itemType, location, suffix),
            payload,
            source=WeatherSource.normalize(source),
            itemType=itemType,
            location=str(location or ""),
            expiresAt=self._expiry(),
        )

    def _get(self, cacheKey: str) -> dict[str, Any] | None:
        if self.store is None:
            return None
        row = self.store.getCache(cacheKey)
        if row is None:
            return None
        expiresAt = str(row.get("expires_at") or row.get("expiresAt") or "")
        if expiresAt and self._expired(expiresAt):
            self.store.deleteCache(cacheKey)
            return None
        payload = dict(row)
        if "payload" in payload and isinstance(payload["payload"], dict):
            payload.update(payload["payload"])
        return payload

    @staticmethod
    def _cacheKey(itemType: str, location: str, suffix: str | int = "") -> str:
        text = str(location or "").strip().lower() or "default"
        tail = f":{suffix}" if str(suffix or "") else ""
        return f"{itemType}:{text}{tail}"

    def _expiry(self) -> str:
        expires = datetime.utcnow() + timedelta(minutes=max(1, int(self.ttlMinutes)))
        return expires.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _expired(timestampText: str) -> bool:
        try:
            expires = datetime.fromisoformat(timestampText.replace("Z", "+00:00"))
            return datetime.utcnow() > expires.replace(tzinfo=None)
        except Exception:
            return False
