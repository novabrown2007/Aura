"""Central weather coordination for Aura."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from modules.weather.alerts import EmergencyAlertMonitor, WeatherThresholdMonitor
from modules.weather.handlers import WeatherEventHandler
from modules.weather.models import WeatherAlert, WeatherData, WeatherForecast, WeatherLocation, WeatherSource, WeatherThreshold
from modules.weather.providers import LocalWeatherProvider, WeatherApiProvider
from modules.weather.storage.sqliteWeatherStore import SQLiteWeatherStore
from modules.weather.ui import ForecastViewModel, WeatherDashboardModel, WeatherViewModel
from modules.weather.weatherAlertManager import WeatherAlertManager
from modules.weather.weatherCacheManager import WeatherCacheManager
from modules.weather.weatherNotificationManager import WeatherNotificationManager
from modules.weather.weatherProviderRouter import WeatherProviderRouter
from modules.weather.weatherQueryEngine import WeatherQueryEngine
from modules.weather.weatherSensorManager import WeatherSensorManager
from modules.weather.weatherMonitor import WeatherMonitor


class WeatherManager:
    """Coordinate weather providers, cache, alerts, and UI-facing views."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Weather") if context and getattr(context, "logger", None) else None
        self.enabled = True
        self.alertsEnabled = True
        self.thresholdNotificationsEnabled = True
        self.localSensorWeatherEnabled = True
        self.weatherApiEnabled = True
        self.cacheEnabled = True
        self.preferredProvider = "openweathermap"
        self.store: SQLiteWeatherStore | None = None
        self.sensorManager: WeatherSensorManager | None = None
        self.localProvider: LocalWeatherProvider | None = None
        self.apiProvider: WeatherApiProvider | None = None
        self.cacheManager: WeatherCacheManager | None = None
        self.providerRouter: WeatherProviderRouter | None = None
        self.queryEngine: WeatherQueryEngine | None = None
        self.notificationManager: WeatherNotificationManager | None = None
        self.alertManager: WeatherAlertManager | None = None
        self.thresholdMonitor: WeatherThresholdMonitor | None = None
        self.emergencyMonitor: EmergencyAlertMonitor | None = None
        self.monitor: WeatherMonitor | None = None
        self.eventHandler: WeatherEventHandler | None = None
        self.locations: dict[str, WeatherLocation] = {}
        self.thresholds: dict[str, WeatherThreshold] = {}
        self.lastCurrentWeather: dict[str, Any] = {}
        self.lastForecast: dict[str, Any] = {}
        self.lastAlerts: list[dict[str, Any]] = []

    def initialize(self, context=None):
        """Bind the manager to a runtime context and load persisted state."""

        if context is not None:
            self.context = context
        if self.context is None:
            return self

        self.logger = self.context.logger.getChild("Weather") if getattr(self.context, "logger", None) else None
        self.enabled = bool(self._configValue("weatherEnabled", True))
        self.alertsEnabled = bool(self._configValue("weatherAlertsEnabled", True))
        self.thresholdNotificationsEnabled = bool(self._configValue("weatherThresholdNotificationsEnabled", True))
        self.localSensorWeatherEnabled = bool(self._configValue("localSensorWeatherEnabled", True))
        self.weatherApiEnabled = bool(self._configValue("weatherApiEnabled", True))
        self.cacheEnabled = bool(self._configValue("weatherForecastCacheEnabled", True))
        self.preferredProvider = str(self._configValue("preferredWeatherProvider", "openweathermap") or "openweathermap")

        self.store = SQLiteWeatherStore(self._storagePath()).initialize()
        self.sensorManager = WeatherSensorManager(self.context).initialize(self.context)
        self.notificationManager = WeatherNotificationManager(self.context).initialize(self.context)
        self.cacheManager = WeatherCacheManager(
            self.context,
            store=self.store if self.cacheEnabled else None,
            ttlMinutes=int(self._configValue("weatherRefreshIntervalMinutes", 15)),
        ).initialize(self.context)
        self.localProvider = LocalWeatherProvider(self.context, sensorManager=self.sensorManager).initialize(self.context)
        self.apiProvider = WeatherApiProvider(self.context, config=self._apiConfig()).initialize(self.context)
        self.providerRouter = WeatherProviderRouter(
            self.context,
            localProvider=self.localProvider if self.localSensorWeatherEnabled else None,
            apiProvider=self.apiProvider if self.weatherApiEnabled else None,
            cacheManager=self.cacheManager if self.cacheEnabled else None,
        ).initialize(self.context)
        self.queryEngine = WeatherQueryEngine(self.context, router=self.providerRouter, sensorManager=self.sensorManager).initialize(self.context)
        self.alertManager = WeatherAlertManager(self.context, store=self.store, notificationManager=self.notificationManager).initialize(self.context)
        self.thresholdMonitor = self.alertManager.thresholdMonitor
        self.emergencyMonitor = self.alertManager.emergencyMonitor
        self.monitor = WeatherMonitor(self.context, manager=self).initialize(self.context)
        self.eventHandler = WeatherEventHandler(self.context, self)

        self._loadPersistedState()
        self._log("Weather manager initialized.")
        return self

    def shutdown(self):
        """Release weather resources."""

        if self.store is not None:
            self.store.close()
        self._log("Weather manager shut down.")

    def getCurrentWeather(self, location: str = "", forceRefresh: bool = False) -> dict[str, Any]:
        payload = self.queryEngine.getCurrentWeather(self.resolveLocation(location), allowCache=not forceRefresh, allowLive=True)
        weather = WeatherData.fromDict(payload)
        self.lastCurrentWeather = payload
        self._storeCurrentWeather(weather)
        self.evaluateThresholds(weather)
        self._emit(WeatherEvents.CURRENT_UPDATED, payload)
        return payload

    def getHourlyForecast(self, location: str = "", hours: int = 24) -> dict[str, Any]:
        payload = self.queryEngine.getHourlyForecast(self.resolveLocation(location), hours=hours)
        self.lastForecast = payload
        self._storeHourlyForecast(WeatherForecast.fromDict(payload), hours=hours)
        self._emit(WeatherEvents.FORECAST_UPDATED, payload)
        return payload

    def getWeeklyForecast(self, location: str = "", days: int = 7) -> dict[str, Any]:
        payload = self.queryEngine.getWeeklyForecast(self.resolveLocation(location), days=days)
        self.lastForecast = payload
        self._storeWeeklyForecast(WeatherForecast.fromDict(payload), days=days)
        self._emit(WeatherEvents.FORECAST_UPDATED, payload)
        return payload

    def getAlerts(self, location: str = "") -> list[dict[str, Any]]:
        alerts = self.queryEngine.getAlerts(self.resolveLocation(location))
        self.lastAlerts = list(alerts)
        if self.alertsEnabled:
            self.alertManager.evaluateAlerts(alerts)
        return alerts

    def getIndoorTemperature(self, location: str = "") -> dict[str, Any]:
        return self.queryEngine.getIndoorTemperature(self.resolveLocation(location))

    def getDashboard(self, location: str = "") -> dict[str, Any]:
        dashboard = self.queryEngine.buildDashboard(self.resolveLocation(location))
        model = WeatherDashboardModel(
            current=dict(dashboard.get("current") or {}),
            forecast={"hourly": dashboard.get("hourly", {}).get("hourly", []), "daily": dashboard.get("weekly", {}).get("daily", [])},
            alerts=list(dashboard.get("alerts") or []),
            sensors=list(self.sensorManager.snapshot().get("sensors", [])),
            thresholds=self.listThresholds(),
            locations=self.listLocations(),
            sourceSnapshot=dict(dashboard.get("sourceSnapshot") or {}),
        )
        return model.asDict()

    def getWeatherViewModel(self, location: str = "") -> dict[str, Any]:
        current = self.getCurrentWeather(location)
        indoor = self.getIndoorTemperature(location)
        return WeatherViewModel(
            location=current.get("location") or self.resolveLocation(location),
            current=current,
            indoorTemperature=indoor.get("temperature"),
            source=current.get("source", WeatherSource.UNKNOWN),
            timestamp=current.get("timestamp") or self._now(),
            metadata={"alertsEnabled": self.alertsEnabled},
        ).asDict()

    def getForecastViewModel(self, location: str = "") -> dict[str, Any]:
        hourly = self.getHourlyForecast(location)
        weekly = self.getWeeklyForecast(location)
        return ForecastViewModel(
            location=self.resolveLocation(location),
            hourly=list(hourly.get("hourly") or []),
            daily=list(weekly.get("daily") or []),
            alerts=list(self.getAlerts(location)),
            source=weekly.get("source") or hourly.get("source") or WeatherSource.UNKNOWN,
            timestamp=weekly.get("timestamp") or hourly.get("timestamp") or self._now(),
            metadata={"preferredProvider": self.preferredProvider},
        ).asDict()

    def addLocation(self, name: str, latitude: float | None = None, longitude: float | None = None, isHome: bool = False, isFavorite: bool = False):
        location = WeatherLocation(
            locationId=self._slug(name),
            name=str(name or ""),
            latitude=latitude,
            longitude=longitude,
            isHome=bool(isHome),
            isFavorite=bool(isFavorite),
        )
        self.locations[location.locationId] = location
        if self.store is not None:
            self.store.upsertLocation(location.asDict())
        return location.asDict()

    def listLocations(self):
        if not self.locations and self.store is not None:
            for row in self.store.listLocations():
                location = WeatherLocation.fromDict(row)
                self.locations[location.locationId or self._slug(location.name)] = location
        return [location.asDict() for location in self.locations.values()]

    def listLocationNames(self):
        return [location.name for location in self.locations.values() if location.name]

    def resolveLocation(self, location: str = "") -> str:
        if location:
            return str(location)
        for saved in self.locations.values():
            if saved.isHome:
                return saved.name
        default = str(self._configValue("defaultLocation", "") or "")
        return default or (next(iter(self.locations.values())).name if self.locations else "")

    def addThreshold(self, **fields):
        threshold = WeatherThreshold.fromDict(fields)
        if not threshold.thresholdId:
            threshold.thresholdId = self._slug(f"{threshold.location}-{threshold.metric}-{threshold.operator}-{threshold.value}")
        self.thresholds[threshold.thresholdId] = threshold
        self.alertManager.registerThreshold(threshold)
        if self.store is not None:
            self.store.upsertThreshold(threshold.asDict())
        return threshold.asDict()

    def listThresholds(self):
        if not self.thresholds and self.store is not None:
            for row in self.store.listThresholds():
                threshold = WeatherThreshold.fromDict(row)
                if threshold.thresholdId:
                    self.thresholds[threshold.thresholdId] = threshold
        return [threshold.asDict() for threshold in self.thresholds.values()]

    def removeThreshold(self, thresholdId: str):
        self.thresholds.pop(str(thresholdId), None)
        self.alertManager.removeThreshold(thresholdId)
        if self.store is not None:
            self.store.deleteThreshold(thresholdId)

    def evaluateThresholds(self, weatherData):
        if not self.thresholdNotificationsEnabled:
            return []
        if not isinstance(weatherData, WeatherData):
            weatherData = WeatherData.fromDict(weatherData)
        return self.alertManager.evaluateWeather(weatherData)

    def refreshCurrentWeather(self, location: str = "", forceRefresh: bool = False):
        return self.getCurrentWeather(location, forceRefresh=forceRefresh)

    def refreshForecast(self, location: str = "", hours: int = 24, days: int = 7):
        self.getHourlyForecast(location, hours=hours)
        return self.getWeeklyForecast(location, days=days)

    def refreshAlerts(self, location: str = ""):
        return self.getAlerts(location)

    def handleEvent(self, event):
        return self.eventHandler.handleEvent(event)

    def snapshot(self):
        return {
            "available": True,
            "enabled": self.enabled,
            "source": self.providerRouter.snapshot() if self.providerRouter is not None else {},
            "currentWeather": dict(self.lastCurrentWeather),
            "forecast": dict(self.lastForecast),
            "alerts": list(self.lastAlerts),
            "thresholds": self.listThresholds(),
            "locations": self.listLocations(),
            "sensors": self.sensorManager.snapshot() if self.sensorManager is not None else {"sensors": [], "count": 0},
            "monitor": self.monitor.snapshot() if self.monitor is not None else {},
            "alertState": self.alertManager.snapshot() if self.alertManager is not None else {},
            "cache": self.cacheManager.snapshot() if self.cacheManager is not None else {},
        }

    def buildResponse(self, location: str = "") -> dict[str, Any]:
        view = self.getWeatherViewModel(location)
        forecast = self.getForecastViewModel(location)
        alerts = self.getAlerts(location)
        spokenText = self._spokenWeatherText(view, forecast)
        uiText = self._uiWeatherText(view, forecast)
        return {
            "spokenText": spokenText,
            "uiText": uiText,
            "notifications": alerts,
            "metadata": {
                "location": view.get("location"),
                "source": view.get("source"),
                "dashboard": self.getDashboard(location),
            },
        }

    def _loadPersistedState(self):
        if self.store is None:
            return
        for row in self.store.listLocations():
            location = WeatherLocation.fromDict(row)
            if location.locationId:
                self.locations[location.locationId] = location
        for row in self.store.listThresholds():
            threshold = WeatherThreshold.fromDict(row)
            if threshold.thresholdId:
                self.thresholds[threshold.thresholdId] = threshold
        self.alertManager.loadThresholds(list(self.thresholds.values()))

    def _storeCurrentWeather(self, weather: WeatherData):
        if self.cacheManager is not None:
            self.cacheManager.setCurrentWeather(weather)

    def _storeHourlyForecast(self, forecast: WeatherForecast, hours: int = 24):
        if self.cacheManager is not None:
            self.cacheManager.setHourlyForecast(forecast, hours=hours)

    def _storeWeeklyForecast(self, forecast: WeatherForecast, days: int = 7):
        if self.cacheManager is not None:
            self.cacheManager.setWeeklyForecast(forecast, days=days)

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        for path in (f"weather.{key}", f"weather.{key[0].lower() + key[1:]}", key):
            try:
                value = config.get(path, None)
            except Exception:
                value = None
            if value is not None:
                return value
        return default

    def _apiConfig(self) -> dict[str, Any]:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return {}
        value = config.get("weather.api", {})
        return dict(value or {})

    def _storagePath(self) -> str:
        path = str(self._configValue("databasePath", "aura_weather.sqlite3") or "aura_weather.sqlite3")
        return str(Path(path))

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload)

    def _log(self, message: str):
        if self.logger:
            self.logger.info(message)

    @staticmethod
    def _slug(value: str) -> str:
        text = str(value or "").strip().lower()
        return "".join(char if char.isalnum() else "-" for char in text).strip("-") or "weather"

    @staticmethod
    def _spokenWeatherText(view: dict[str, Any], forecast: dict[str, Any]) -> str:
        current = dict(view.get("current") or {})
        temperature = current.get("temperature")
        condition = current.get("condition") or "weather"
        if temperature is None:
            return f"Weather for {view.get('location') or 'your area'} is available."
        return f"It's currently {int(round(float(temperature)))} degrees and {condition}."

    @staticmethod
    def _uiWeatherText(view: dict[str, Any], forecast: dict[str, Any]) -> str:
        current = dict(view.get("current") or {})
        lines = [
            f"Location: {view.get('location') or 'Unknown'}",
            f"Temperature: {current.get('temperature', 'n/a')}°",
            f"Humidity: {current.get('humidity', 'n/a')}%",
            f"Condition: {current.get('condition', 'n/a')}",
            f"Source: {current.get('source', 'UNKNOWN')}",
        ]
        daily = list(forecast.get("daily") or [])
        if daily:
            lines.append("")
            lines.append("Forecast:")
            for day in daily[:3]:
                lines.append(f"- {day.get('day', day.get('name', 'Day'))}: {day.get('condition', 'n/a')}")
        return "\n".join(lines)


from modules.weather.weatherEvents import WeatherEvents
