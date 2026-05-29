"""Smart home module action definitions."""

from core.modules.base.moduleAction import ModuleAction

SMART_HOME_ACTIONS = (
    ModuleAction(
        name="smartHome.light.turnOn",
        description="Turn on a light.",
        method="turnLightOn",
        parameters={"room": {"type": "string"}},
        capabilities=("smart-home.control",),
    ),
    ModuleAction(
        name="smartHome.light.turnOff",
        description="Turn off a light.",
        method="turnLightOff",
        parameters={"room": {"type": "string"}},
        capabilities=("smart-home.control",),
    ),
    ModuleAction(
        name="smartHome.light.setColor",
        description="Set a light color.",
        method="setLightColor",
        parameters={"room": {"type": "string"}, "color": {"type": "string"}},
        requiredParameters=("room", "color"),
        capabilities=("smart-home.control",),
    ),
)
