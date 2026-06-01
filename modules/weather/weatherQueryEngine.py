"""Weather query orchestration for Aura."""

from __future__ import annotations

from typing import Any

from modules.weather.models import WeatherSource


class WeatherQueryEngine:
    """Coordinate current weather, forecast, and sensor queries."""

    def __init__(self, context=None, router=None, sensorManager=None):
        self.context = context
        self.router = router
        self.sensorManager = sensorManager
        self.logger = context.logger.getChild("Weather.Query") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Query") if getattr(context, "logger", None) else None
        return self

    def getCurrentWeather(self, location: str = "", allowCache: bool = True, allowLive: bool = True) -> dict[str, Any]:
        weather = self.router.getCurrentWeather(location, allowCache=allowCache, allowLive=allowLive)
        payload = weather.asDict()
        payload["source"] = WeatherSource.normalize(payload.get("source"))
        return payload

    def getHourlyForecast(self, location: str = "", hours: int = 24, allowCache: bool = True, allowLive: bool = True) -> dict[str, Any]:
        forecast = self.router.getHourlyForecast(location, hours=hours, allowCache=allowCache, allowLive=allowLive)
        payload = forecast.asDict()
        payload["source"] = WeatherSource.normalize(payload.get("source"))
        return payload

    def getWeeklyForecast(self, location: str = "", days: int = 7, allowCache: bool = True, allowLive: bool = True) -> dict[str, Any]:
        forecast = self.router.getWeeklyForecast(location, days=days, allowCache=allowCache, allowLive=allowLive)
        payload = forecast.asDict()
        payload["source"] = WeatherSource.normalize(payload.get("source"))
        return payload

    def getAlerts(self, location: str = "", allowCache: bool = True, allowLive: bool = True) -> list[dict[str, Any]]:
        return list(self.router.getAlerts(location, allowCache=allowCache, allowLive=allowLive))

    def getIndoorTemperature(self, location: str = "") -> dict[str, Any]:
        if self.sensorManager is not None:
            temperature = self.sensorManager.getIndoorTemperature(location)
            if temperature is not None:
                return {
                    "location": location or self._defaultLocation(),
                    "temperature": temperature,
                    "source": WeatherSource.LOCAL_SENSOR,
                }
        temperature = self.router.getIndoorTemperature(location)
        return {
            "location": location or self._defaultLocation(),
            "temperature": temperature,
            "source": WeatherSource.LOCAL_SENSOR if temperature is not None else WeatherSource.UNKNOWN,
        }

    def buildDashboard(self, location: str = "") -> dict[str, Any]:
        current = self.getCurrentWeather(location)
        hourly = self.getHourlyForecast(location)
        weekly = self.getWeeklyForecast(location)
        alerts = self.getAlerts(location)
        indoor = self.getIndoorTemperature(location)
        return {
            "location": current.get("location") or location or self._defaultLocation(),
            "current": current,
            "hourly": hourly,
            "weekly": weekly,
            "alerts": alerts,
            "indoorTemperature": indoor.get("temperature"),
            "sourceSnapshot": self.router.snapshot(),
        }

    def compareLocations(self, first: str, second: str) -> dict[str, Any]:
        firstWeather = self.getCurrentWeather(first)
        secondWeather = self.getCurrentWeather(second)
        return {
            "first": firstWeather,
            "second": secondWeather,
            "temperatureDifference": self._difference(firstWeather.get("temperature"), secondWeather.get("temperature")),
            "humidityDifference": self._difference(firstWeather.get("humidity"), secondWeather.get("humidity")),
        }

    def _defaultLocation(self) -> str:
        config = getattr(self.context, "config", None)
        if config is not None and hasattr(config, "get"):
            return str(config.get("weather.defaultLocation", "") or "")
        return ""

    @staticmethod
    def _difference(first, second):
        try:
            return None if first is None or second is None else float(first) - float(second)
        except Exception:
            return None
