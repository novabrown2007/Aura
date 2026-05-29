"""Mock weather capability module for Aura."""

from __future__ import annotations

from datetime import datetime

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata
from modules.weather.weatherActions import WEATHER_ACTIONS
from modules.weather.weatherEvents import WeatherEvents
from modules.weather.weatherIntents import WEATHER_INTENTS
from modules.weather.weatherPermissions import WEATHER_PERMISSIONS


class WeatherModule(AuraModule):
    """Deterministic weather capability placeholder."""

    metadata = ModuleMetadata(
        name="weather",
        version="1.0.0",
        author="Aura",
        description="Local weather capability placeholder.",
        permissions=tuple(WEATHER_PERMISSIONS.asList()),
        capabilities=("weather.read", "weather.forecast"),
    )

    def __init__(self, context=None):
        super().__init__()
        self.lastQuery = {}
        self._lastHandledEvent = ""
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        self.lastQuery = {}
        self._lastHandledEvent = ""
        if self.logger:
            self.logger.info("weather module started.")

    def getIntents(self):
        return list(WEATHER_INTENTS)

    def getActions(self):
        return list(WEATHER_ACTIONS)

    def getPermissions(self):
        return WEATHER_PERMISSIONS

    def getSubscriptions(self):
        return ["conversation.started"]

    def handleEvent(self, event):
        self._lastHandledEvent = getattr(event, "name", "")
        return None

    def getCurrentWeather(self, location: str = "") -> dict[str, object]:
        """Return a deterministic placeholder weather snapshot."""

        self.lastQuery = {"location": str(location or "")}
        self.emit(WeatherEvents.REQUESTED, {"location": str(location or "")})
        result = {
            "location": str(location or "Unknown"),
            "condition": "clear",
            "temperatureC": 21,
            "observedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.emit(WeatherEvents.RESPONSE, result)
        return result

    def getForecast(self, location: str = "", days: int = 3) -> dict[str, object]:
        """Return a deterministic placeholder forecast snapshot."""

        self.lastQuery = {"location": str(location or ""), "days": int(days)}
        forecast = [
            {"day": index + 1, "condition": "clear", "highC": 22 + index, "lowC": 14 + index}
            for index in range(max(1, int(days)))
        ]
        result = {
            "location": str(location or "Unknown"),
            "days": int(days),
            "forecast": forecast,
        }
        self.emit(WeatherEvents.RESPONSE, result)
        return result

    def handleIntent(self, intent):
        """Handle weather intents through the placeholder actions."""

        intentName = getattr(intent, "name", intent)
        if intentName == "weather.current":
            return self.getCurrentWeather(getattr(intent, "arguments", {}).get("location", ""))
        if intentName == "weather.forecast":
            arguments = getattr(intent, "arguments", {})
            return self.getForecast(arguments.get("location", ""), arguments.get("days", 3))
        raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")
