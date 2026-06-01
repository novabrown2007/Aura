"""Weather action definitions for Aura."""

from core.modules.base.moduleAction import ModuleAction

WEATHER_ACTIONS = (
    ModuleAction(
        name="weather.getCurrent",
        description="Return current weather for a location.",
        method="getCurrentWeather",
        parameters={"location": {"type": "string"}},
        requiredParameters=(),
        capabilities=("weather.read",),
    ),
    ModuleAction(
        name="weather.getHourlyForecast",
        description="Return an hourly forecast for a location.",
        method="getHourlyForecast",
        parameters={"location": {"type": "string"}, "hours": {"type": "integer"}},
        requiredParameters=(),
        capabilities=("weather.forecast",),
    ),
    ModuleAction(
        name="weather.getWeeklyForecast",
        description="Return a weekly forecast for a location.",
        method="getWeeklyForecast",
        parameters={"location": {"type": "string"}, "days": {"type": "integer"}},
        requiredParameters=(),
        capabilities=("weather.forecast",),
    ),
    ModuleAction(
        name="weather.getIndoorTemperature",
        description="Return the current indoor temperature from connected sensors.",
        method="getIndoorTemperature",
        parameters={"location": {"type": "string"}},
        requiredParameters=(),
        capabilities=("weather.read",),
    ),
    ModuleAction(
        name="weather.addLocation",
        description="Save a location for later weather lookups.",
        method="addLocation",
        parameters={"name": {"type": "string"}},
        requiredParameters=("name",),
        capabilities=("weather.write",),
    ),
    ModuleAction(
        name="weather.listLocations",
        description="List saved weather locations.",
        method="listLocations",
        parameters={},
        requiredParameters=(),
        capabilities=("weather.read",),
    ),
)
