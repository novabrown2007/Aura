"""Automation Composer module for Aura."""

from modules.base import ModuleMetadata
from modules.automation_composer.automationComposer import AutomationComposer


MODULE_METADATA = ModuleMetadata(
    name="automationComposer",
    version="0.1.0",
    description="Draft, activate, and run reviewable assistant automations.",
    dependencies=(),
    permissions=("database:read", "database:write", "events:write", "tools:execute"),
    capabilities=("automation", "autonomy"),
)


def createModule(_context=None):
    """Create the Automation Composer module."""

    return AutomationComposer()
