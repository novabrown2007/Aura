"""Route execution requests to the correct subsystem."""

from __future__ import annotations

from assistant.execution.routing import AutomationActionRouter, BridgeActionRouter, ModuleActionRouter


class ExecutionRouter:
    """Select the correct router for one action."""

    def __init__(self, context=None):
        self.context = context
        self.moduleRouter = ModuleActionRouter(context)
        self.bridgeRouter = BridgeActionRouter(context)
        self.automationRouter = AutomationActionRouter(context)

    def route(self, request, actionDefinition, confirmed: bool = False, allowAdmin: bool = False):
        actionName = str(getattr(actionDefinition, "actionName", "") or getattr(request, "action", "") or "")
        category = str(getattr(actionDefinition, "category", "") or "").upper()
        if actionName.startswith("bridge.") or category == "BRIDGE":
            return self.bridgeRouter.route(request, actionDefinition, confirmed=confirmed, allowAdmin=allowAdmin)
        if actionName.startswith("automation.") or category == "AUTOMATION":
            return self.automationRouter.route(request, actionDefinition, confirmed=confirmed, allowAdmin=allowAdmin)
        return self.moduleRouter.route(request, actionDefinition, confirmed=confirmed, allowAdmin=allowAdmin)
