"""Weather module permission definitions."""

from core.modules.modulePermissions import ModulePermissions

WEATHER_PERMISSIONS = ModulePermissions(
    capabilityPermissions=("weather.read", "weather.forecast"),
    externalApiPermissions=("network:http",),
)
