"""Weather module permission definitions."""

from core.modules.modulePermissions import ModulePermissions

WEATHER_PERMISSIONS = ModulePermissions(
    capabilityPermissions=("weather.read", "weather.forecast", "weather.alerts", "weather.thresholds", "weather.write"),
    externalApiPermissions=("network:http",),
    deviceAccessPermissions=("homeAutomation.read",),
)
