"""Smart home module intent definitions."""

from core.modules.base.moduleIntent import ModuleIntent

SMART_HOME_INTENTS = (
    ModuleIntent(
        name="smartHome.light.turnOn",
        description="Turn on a light.",
        arguments={"room": {"type": "string"}},
        target="turnLightOn",
    ),
    ModuleIntent(
        name="smartHome.light.turnOff",
        description="Turn off a light.",
        arguments={"room": {"type": "string"}},
        target="turnLightOff",
    ),
    ModuleIntent(
        name="smartHome.light.setColor",
        description="Set a light color.",
        arguments={"room": {"type": "string"}, "color": {"type": "string"}},
        target="setLightColor",
        requiredArguments=("room", "color"),
    ),
)
