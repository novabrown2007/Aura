"""Weather module intent definitions."""

from core.modules.base.moduleIntent import ModuleIntent

WEATHER_INTENTS = (
    ModuleIntent(
        name="weather.current",
        description="Get the current weather for a location.",
        arguments={"location": {"type": "string"}},
        target="getCurrentWeather",
        requiredArguments=("location",),
    ),
    ModuleIntent(
        name="weather.forecast",
        description="Get a short forecast for a location.",
        arguments={"location": {"type": "string"}, "days": {"type": "integer"}},
        target="getForecast",
        requiredArguments=("location",),
    ),
)
