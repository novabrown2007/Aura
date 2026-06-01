"""Aura weather capability module."""

from __future__ import annotations

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.base.moduleSubscription import ModuleSubscription
from core.modules.modulePermissions import ModulePermissions
from core.tools.tool import Tool
from modules.weather.actions import WEATHER_ACTIONS, WEATHER_ALERT_ACTIONS
from modules.weather.handlers import WeatherEventHandler
from modules.weather.intents import WEATHER_INTENTS
from modules.weather.weatherManager import WeatherManager
from modules.weather.weatherPermissions import WEATHER_PERMISSIONS


class WeatherModule(AuraModule):
    """Unified environmental awareness capability for Aura."""

    metadata = ModuleMetadata(
        name="weather",
        version="1.0.0",
        author="Aura",
        description="Unified environmental awareness system for local sensors, forecasts, alerts, and thresholds.",
        permissions=tuple(WEATHER_PERMISSIONS.asList()),
        capabilities=("weather.read", "weather.forecast", "weather.alerts", "weather.thresholds", "weather.write"),
    )

    def __init__(self, context=None):
        super().__init__()
        self.manager: WeatherManager | None = None
        self.eventHandler: WeatherEventHandler | None = None
        self.permissions = WEATHER_PERMISSIONS
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        self.manager = WeatherManager(context).initialize(context)
        self.eventHandler = self.manager.eventHandler
        self.permissions = WEATHER_PERMISSIONS
        self._logStartup("weather module started.")
        return self

    def shutdown(self):
        if self.manager is not None:
            self.manager.shutdown()

    def getIntents(self):
        return list(WEATHER_INTENTS)

    def getActions(self):
        return list((*WEATHER_ACTIONS, *WEATHER_ALERT_ACTIONS))

    def getSubscriptions(self):
        return [
            ModuleSubscription(eventName="bridge.sensor.updated", handler="handleEvent"),
            ModuleSubscription(eventName="schedule.tick", handler="handleEvent"),
            ModuleSubscription(eventName="system.started", handler="handleEvent"),
            ModuleSubscription(eventName="location.updated", handler="handleEvent"),
        ]

    def getPermissions(self):
        return self.permissions

    def getTools(self):
        return [
            Tool(
                name="weather.getCurrent",
                description="Get current weather for a location.",
                parameters={"location": {"type": "string"}},
                module="weather",
                method="getCurrentWeather",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.read",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.getHourlyForecast",
                description="Get an hourly weather forecast.",
                parameters={"location": {"type": "string"}, "hours": {"type": "integer"}},
                module="weather",
                method="getHourlyForecast",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.forecast",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.getWeeklyForecast",
                description="Get a weekly weather forecast.",
                parameters={"location": {"type": "string"}, "days": {"type": "integer"}},
                module="weather",
                method="getWeeklyForecast",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.forecast",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.getIndoorTemperature",
                description="Get the indoor temperature from connected sensors.",
                parameters={"location": {"type": "string"}},
                module="weather",
                method="getIndoorTemperature",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.read",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.getAlerts",
                description="Get weather alerts for a location.",
                parameters={"location": {"type": "string"}},
                module="weather",
                method="getAlerts",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.alerts",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.addThreshold",
                description="Create a weather threshold rule.",
                parameters={
                    "metric": {"type": "string"},
                    "operator": {"type": "string"},
                    "value": {"type": "number"},
                    "location": {"type": "string"},
                },
                module="weather",
                method="addThreshold",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.thresholds",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.addLocation",
                description="Save a weather location for later use.",
                parameters={
                    "name": {"type": "string"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "isHome": {"type": "boolean"},
                    "isFavorite": {"type": "boolean"},
                },
                module="weather",
                method="addLocation",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.write",),
                riskLevel="LOW",
            ),
            Tool(
                name="weather.listLocations",
                description="List saved weather locations.",
                parameters={},
                module="weather",
                method="listLocations",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("weather.read",),
                riskLevel="LOW",
            ),
        ]

    def handleEvent(self, event):
        if self.manager is None:
            return None
        return self.manager.handleEvent(event)

    def handleIntent(self, intent):
        intentName = getattr(intent, "name", intent)
        data = dict(getattr(intent, "data", {}) or getattr(intent, "arguments", {}) or {})
        if self.manager is None:
            return self._standaloneIntent(intentName, data)
        if intentName == "weather.current":
            return self.manager.getCurrentWeather(data.get("location", ""))
        if intentName in {"weather.forecast", "weather.weeklyForecast"}:
            return self.manager.getWeeklyForecast(data.get("location", ""), int(data.get("days", 7) or 7))
        if intentName == "weather.hourlyForecast":
            return self.manager.getHourlyForecast(data.get("location", ""), int(data.get("hours", 24) or 24))
        if intentName == "weather.alerts":
            return self.manager.getAlerts(data.get("location", ""))
        if intentName == "weather.indoorTemperature":
            return self.manager.getIndoorTemperature(data.get("location", ""))
        if intentName == "weather.addThreshold":
            return self.manager.addThreshold(**data)
        if intentName == "weather.addLocation":
            return self.manager.addLocation(
                data.get("name", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                isHome=bool(data.get("isHome", data.get("is_home", False))),
                isFavorite=bool(data.get("isFavorite", data.get("is_favorite", False))),
            )
        if intentName == "weather.listLocations":
            return self.manager.listLocations()
        raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")

    def snapshot(self):
        return self.manager.snapshot() if self.manager is not None else {"available": False, "enabled": False}

    def getCurrentWeather(self, location: str = ""):
        if self.manager is not None:
            return self.manager.getCurrentWeather(location)
        return self._fallbackCurrentWeather(location)

    def getHourlyForecast(self, location: str = "", hours: int = 24):
        if self.manager is not None:
            return self.manager.getHourlyForecast(location, hours=hours)
        return self._fallbackHourlyForecast(location, hours=hours)

    def getWeeklyForecast(self, location: str = "", days: int = 7):
        if self.manager is not None:
            return self.manager.getWeeklyForecast(location, days=days)
        return self._fallbackWeeklyForecast(location, days=days)

    def getIndoorTemperature(self, location: str = ""):
        if self.manager is not None:
            return self.manager.getIndoorTemperature(location)
        return {"location": location or "Local", "temperature": 20.0, "source": "SIMULATED"}

    def getAlerts(self, location: str = ""):
        if self.manager is not None:
            return self.manager.getAlerts(location)
        return []

    def addLocation(self, name: str, latitude: float | None = None, longitude: float | None = None, isHome: bool = False, isFavorite: bool = False):
        if self.manager is not None:
            return self.manager.addLocation(name, latitude=latitude, longitude=longitude, isHome=isHome, isFavorite=isFavorite)
        return {
            "locationId": self._slug(name),
            "name": str(name or ""),
            "latitude": latitude,
            "longitude": longitude,
            "isHome": bool(isHome),
            "isFavorite": bool(isFavorite),
        }

    def listLocations(self):
        if self.manager is not None:
            return self.manager.listLocations()
        return []

    def addThreshold(self, **fields):
        if self.manager is not None:
            return self.manager.addThreshold(**fields)
        return {"thresholdId": "threshold", **fields}

    def listThresholds(self):
        if self.manager is not None:
            return self.manager.listThresholds()
        return []

    def buildResponse(self, location: str = ""):
        if self.manager is not None:
            return self.manager.buildResponse(location)
        current = self.getCurrentWeather(location)
        forecast = self.getWeeklyForecast(location)
        spokenText = self._fallbackSpokenText(current)
        uiText = (
            f"Location: {current.get('location')}\n"
            f"Temperature: {current.get('temperature')} degrees\n"
            f"Condition: {current.get('condition')}\n"
            f"Source: {current.get('source')}"
        )
        return {"spokenText": spokenText, "uiText": uiText, "notifications": [], "metadata": {"location": current.get("location"), "forecast": forecast}}

    def _standaloneIntent(self, intentName: str, data: dict):
        if intentName == "weather.current":
            return self._fallbackCurrentWeather(data.get("location", ""))
        if intentName in {"weather.forecast", "weather.weeklyForecast"}:
            return self._fallbackWeeklyForecast(data.get("location", ""), int(data.get("days", 7) or 7))
        if intentName == "weather.hourlyForecast":
            return self._fallbackHourlyForecast(data.get("location", ""), int(data.get("hours", 24) or 24))
        if intentName == "weather.alerts":
            return []
        if intentName == "weather.indoorTemperature":
            return {"location": data.get("location", "") or "Local", "temperature": 20.0, "source": "SIMULATED"}
        if intentName == "weather.addThreshold":
            return {"thresholdId": "threshold", **data}
        if intentName == "weather.addLocation":
            return {"locationId": self._slug(data.get("name", "")), "name": str(data.get("name") or "")}
        if intentName == "weather.listLocations":
            return []
        raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")

    @staticmethod
    def _fallbackCurrentWeather(location: str):
        return {
            "location": location or "Toronto",
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.0,
            "windSpeed": 5.0,
            "windDirection": "N",
            "condition": "clear",
            "visibility": 10.0,
            "uvIndex": 2.0,
            "feelsLike": 20.0,
            "source": "SIMULATED",
            "timestamp": "2026-05-31 00:00:00",
            "metadata": {"fallback": True},
        }

    @staticmethod
    def _fallbackHourlyForecast(location: str, hours: int = 24):
        return {
            "location": location or "Toronto",
            "source": "SIMULATED",
            "timestamp": "2026-05-31 00:00:00",
            "hourly": [{"hour": index + 1, "temperature": 20.0 + index * 0.5, "condition": "clear"} for index in range(max(1, int(hours)))],
            "daily": [],
            "alerts": [],
            "metadata": {"fallback": True},
        }

    @staticmethod
    def _fallbackWeeklyForecast(location: str, days: int = 7):
        return {
            "location": location or "Toronto",
            "source": "SIMULATED",
            "timestamp": "2026-05-31 00:00:00",
            "hourly": [],
            "daily": [{"day": index + 1, "condition": "clear", "highC": 22 + index, "lowC": 14 + index} for index in range(max(1, int(days)))],
            "alerts": [],
            "metadata": {"fallback": True},
        }

    @staticmethod
    def _fallbackSpokenText(current: dict[str, object]) -> str:
        temperature = current.get("temperature")
        condition = current.get("condition") or "weather"
        return f"It's currently {int(round(float(temperature)))} degrees and {condition}." if temperature is not None else "Weather data is available."

    @staticmethod
    def _slug(value: str) -> str:
        text = str(value or "").strip().lower()
        return "".join(char if char.isalnum() else "-" for char in text).strip("-") or "weather"
