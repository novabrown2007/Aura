"""Execute routed Aura actions."""

from __future__ import annotations


class ActionExecutor:
    """Execute an action through the configured router."""

    def __init__(self, context=None):
        self.context = context

    def execute(self, request, actionDefinition, router, confirmed: bool = False, allowAdmin: bool = False):
        if router is None:
            raise RuntimeError("Execution router unavailable.")
        return router.route(request, actionDefinition, confirmed=confirmed, allowAdmin=allowAdmin)
