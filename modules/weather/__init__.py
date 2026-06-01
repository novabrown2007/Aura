"""Weather capability module for Aura."""

from modules.weather.actions import WEATHER_ACTIONS, WEATHER_ALERT_ACTIONS
from modules.weather.intents import WEATHER_INTENTS
from modules.weather.weatherEvents import WeatherEvents
from modules.weather.weatherModule import WeatherModule
from modules.weather.weatherPermissions import WEATHER_PERMISSIONS

MODULE_METADATA = WeatherModule.metadata


def createModule(context=None):
    """Create the weather Aura module."""

    return WeatherModule(context)


def register(context):
    """Register the weather module with the runtime context."""

    context.weather = WeatherModule(context)


__all__ = [
    "MODULE_METADATA",
    "WeatherEvents",
    "WEATHER_ACTIONS",
    "WEATHER_ALERT_ACTIONS",
    "WEATHER_INTENTS",
    "WEATHER_PERMISSIONS",
    "WeatherModule",
    "createModule",
    "register",
]
