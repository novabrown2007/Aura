"""Route automation actions."""

from __future__ import annotations


class AutomationActionRouter:
    """Placeholder automation router for future workflow execution."""

    def __init__(self, context=None):
        self.context = context

    def route(self, request, actionDefinition, confirmed: bool = False, allowAdmin: bool = False):
        automation = getattr(self.context, "autonomousTasks", None)
        if automation is None:
            raise RuntimeError("Automation runtime unavailable.")
        if hasattr(automation, "runAction"):
            return automation.runAction(actionDefinition.actionName, dict(getattr(request, "parameters", {}) or {}))
        raise RuntimeError("Automation router unavailable.")
