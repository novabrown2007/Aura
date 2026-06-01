"""Weather intent definitions for Aura."""

from core.modules.base.moduleIntent import ModuleIntent

WEATHER_INTENTS = (
    ModuleIntent(
        name="weather.current",
        description="Get current weather for a location.",
        arguments={"location": {"type": "string"}},
        target="getCurrentWeather",
    ),
    ModuleIntent(
        name="weather.forecast",
        description="Get a forecast for a location.",
        arguments={"location": {"type": "string"}, "days": {"type": "integer"}},
        target="getWeeklyForecast",
    ),
    ModuleIntent(
        name="weather.hourlyForecast",
        description="Get hourly weather for a location.",
        arguments={"location": {"type": "string"}, "hours": {"type": "integer"}},
        target="getHourlyForecast",
    ),
    ModuleIntent(
        name="weather.weeklyForecast",
        description="Get weekly weather for a location.",
        arguments={"location": {"type": "string"}, "days": {"type": "integer"}},
        target="getWeeklyForecast",
    ),
    ModuleIntent(
        name="weather.alerts",
        description="Get weather alerts for a location.",
        arguments={"location": {"type": "string"}},
        target="getAlerts",
    ),
    ModuleIntent(
        name="weather.indoorTemperature",
        description="Get the local indoor temperature.",
        arguments={"location": {"type": "string"}},
        target="getIndoorTemperature",
    ),
    ModuleIntent(
        name="weather.addThreshold",
        description="Create a threshold alert rule.",
        arguments={"metric": {"type": "string"}, "operator": {"type": "string"}, "value": {"type": "number"}},
        target="addThreshold",
    ),
    ModuleIntent(
        name="weather.addLocation",
        description="Save a weather location.",
        arguments={"name": {"type": "string"}},
        target="addLocation",
    ),
)
