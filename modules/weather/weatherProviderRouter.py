"""Weather provider selection and fallback logic for Aura."""

from __future__ import annotations

from datetime import datetime

from modules.weather.models import WeatherData, WeatherForecast, WeatherSource


class WeatherProviderRouter:
    """Choose the best available weather source in priority order."""

    def __init__(self, context=None, localProvider=None, apiProvider=None, cacheManager=None):
        self.context = context
        self.localProvider = localProvider
        self.apiProvider = apiProvider
        self.cacheManager = cacheManager
        self.logger = context.logger.getChild("Weather.Router") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Router") if getattr(context, "logger", None) else None
        return self

    def getCurrentWeather(self, location: str = "", allowCache: bool = True, allowLive: bool = True) -> WeatherData:
        """Return current weather using local sensors, cache, live API, or simulated fallback."""

        if self._localEnabled():
            weather = self.localProvider.getCurrentWeather(location) if self.localProvider else None
            if weather is not None:
                return self._finalizeCurrent(weather)

        if allowCache and self.cacheManager is not None:
            cached = self.cacheManager.getCurrentWeather(location)
            if cached is not None:
                cached.source = WeatherSource.CACHED_API
                return self._finalizeCurrent(cached)

        if allowLive and self._apiEnabled():
            weather = self.apiProvider.getCurrentWeather(location) if self.apiProvider else None
            if weather is not None:
                weather.source = WeatherSource.WEATHER_API
                if self.cacheManager is not None:
                    self.cacheManager.setCurrentWeather(weather)
                return self._finalizeCurrent(weather)

        weather = self._simulateCurrent(location)
        return self._finalizeCurrent(weather)

    def getHourlyForecast(self, location: str = "", hours: int = 24, allowCache: bool = True, allowLive: bool = True) -> WeatherForecast:
        if allowCache and self.cacheManager is not None:
            cached = self.cacheManager.getHourlyForecast(location, hours=hours)
            if cached is not None:
                cached.source = WeatherSource.CACHED_API
                return cached
        if allowLive and self._apiEnabled():
            forecast = self.apiProvider.getHourlyForecast(location, hours=hours) if self.apiProvider else None
            if forecast is not None:
                forecast.source = WeatherSource.WEATHER_API
                if self.cacheManager is not None:
                    self.cacheManager.setHourlyForecast(forecast, hours=hours)
                return forecast
        return WeatherForecast(
            location=str(location or "Unknown"),
            source=WeatherSource.SIMULATED,
            timestamp=self._now(),
            hourly=[],
            daily=[],
            alerts=[],
            metadata={"reason": "fallback"},
        )

    def getWeeklyForecast(self, location: str = "", days: int = 7, allowCache: bool = True, allowLive: bool = True) -> WeatherForecast:
        if allowCache and self.cacheManager is not None:
            cached = self.cacheManager.getWeeklyForecast(location, days=days)
            if cached is not None:
                cached.source = WeatherSource.CACHED_API
                return cached
        if allowLive and self._apiEnabled():
            forecast = self.apiProvider.getWeeklyForecast(location, days=days) if self.apiProvider else None
            if forecast is not None:
                forecast.source = WeatherSource.WEATHER_API
                if self.cacheManager is not None:
                    self.cacheManager.setWeeklyForecast(forecast, days=days)
                return forecast
        return WeatherForecast(
            location=str(location or "Unknown"),
            source=WeatherSource.SIMULATED,
            timestamp=self._now(),
            hourly=[],
            daily=[],
            alerts=[],
            metadata={"reason": "fallback"},
        )

    def getAlerts(self, location: str = "", allowCache: bool = True, allowLive: bool = True) -> list[dict]:
        if allowCache and self.cacheManager is not None:
            cached = self.cacheManager.getAlerts(location)
            if cached:
                return list(cached)
        if allowLive and self._apiEnabled() and self.apiProvider is not None:
            alerts = self.apiProvider.getAlerts(location)
            if alerts and self.cacheManager is not None:
                self.cacheManager.setAlerts(location, [alert.asDict() for alert in alerts])
            return [alert.asDict() for alert in alerts]
        return []

    def getIndoorTemperature(self, location: str = ""):
        if self.localProvider is None:
            return None
        return self.localProvider.getIndoorTemperature(location)

    def snapshot(self) -> dict:
        return {
            "localEnabled": self._localEnabled(),
            "apiEnabled": self._apiEnabled(),
            "cacheEnabled": self.cacheManager is not None,
            "preferredProvider": self._configValue("preferredWeatherProvider", "openweathermap"),
        }

    def _finalizeCurrent(self, weather: WeatherData) -> WeatherData:
        if weather.timestamp:
            return weather
        weather.timestamp = self._now()
        return weather

    def _simulateCurrent(self, location: str) -> WeatherData:
        return WeatherData(
            location=str(location or "Unknown"),
            temperature=20.0,
            humidity=50.0,
            pressure=1013.0,
            windSpeed=5.0,
            windDirection="N",
            condition="simulated",
            visibility=10.0,
            uvIndex=2.0,
            feelsLike=20.0,
            source=WeatherSource.SIMULATED,
            timestamp=self._now(),
            metadata={"reason": "fallback"},
        )

    def _localEnabled(self) -> bool:
        return bool(self._configValue("localSensorWeatherEnabled", True)) and self.localProvider is not None and self.localProvider.isAvailable()

    def _apiEnabled(self) -> bool:
        return bool(self._configValue("weatherApiEnabled", True)) and self.apiProvider is not None and self.apiProvider.isAvailable()

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(f"weather.{key}", default)

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
