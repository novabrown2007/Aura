"""Home automation module package for Aura."""

from modules.home_automation.homeAutomation import HomeAutomation

__all__ = ["HomeAutomation"]


def register(context):
    """Register the home automation module with the runtime context."""

    context.homeAutomation = HomeAutomation(context)
