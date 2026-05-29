"""Smart home module permission definitions."""

from core.modules.modulePermissions import ModulePermissions

SMART_HOME_PERMISSIONS = ModulePermissions(
    capabilityPermissions=("smart-home.control", "smart-home.status"),
    deviceAccessPermissions=("home:lights", "home:devices"),
)
