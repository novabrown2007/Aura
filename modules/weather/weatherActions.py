"""Weather module action definitions."""

from core.modules.base.moduleAction import ModuleAction

WEATHER_ACTIONS = (
    ModuleAction(
        name="weather.getCurrent",
        description="Return the current weather snapshot.",
        method="getCurrentWeather",
        parameters={"location": {"type": "string"}},
        requiredParameters=("location",),
        capabilities=("weather.read",),
    ),
    ModuleAction(
        name="weather.getForecast",
        description="Return a short forecast snapshot.",
        method="getForecast",
        parameters={"location": {"type": "string"}, "days": {"type": "integer"}},
        requiredParameters=("location",),
        capabilities=("weather.forecast",),
    ),
)
