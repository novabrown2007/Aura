"""Weather alert action definitions for Aura."""

from core.modules.base.moduleAction import ModuleAction

WEATHER_ALERT_ACTIONS = (
    ModuleAction(
        name="weather.getAlerts",
        description="Return weather alerts for a location.",
        method="getAlerts",
        parameters={"location": {"type": "string"}},
        requiredParameters=(),
        capabilities=("weather.alerts",),
    ),
    ModuleAction(
        name="weather.addThreshold",
        description="Create a weather threshold notification rule.",
        method="addThreshold",
        parameters={
            "metric": {"type": "string"},
            "operator": {"type": "string"},
            "value": {"type": "number"},
            "location": {"type": "string"},
        },
        requiredParameters=("metric", "operator", "value"),
        capabilities=("weather.thresholds",),
    ),
)
