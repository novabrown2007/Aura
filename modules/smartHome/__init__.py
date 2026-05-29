"""Smart home capability module for Aura."""

from modules.smartHome.smartHomeActions import SMART_HOME_ACTIONS
from modules.smartHome.smartHomeEvents import SmartHomeEvents
from modules.smartHome.smartHomeIntents import SMART_HOME_INTENTS
from modules.smartHome.smartHomeModule import SmartHomeModule
from modules.smartHome.smartHomePermissions import SMART_HOME_PERMISSIONS

MODULE_METADATA = SmartHomeModule.metadata


def createModule(context=None):
    """Create the smart home Aura module."""

    return SmartHomeModule()


def register(context):
    """Register the smart home module with the runtime context."""

    context.smartHome = SmartHomeModule(context)


__all__ = [
    "MODULE_METADATA",
    "SMART_HOME_ACTIONS",
    "SMART_HOME_INTENTS",
    "SMART_HOME_PERMISSIONS",
    "SmartHomeEvents",
    "SmartHomeModule",
    "createModule",
    "register",
]
