"""Final execution guard for Aura governance."""

from __future__ import annotations


class ExecutionGuard:
    """Prevent action bypasses after policy validation."""

    def __init__(self, context=None, safetyManager=None):
        self.context = context
        self.safetyManager = safetyManager or getattr(context, "safetyManager", None)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Guard") if logger else None

    def canExecute(self, request, tool=None, confirmed: bool = False, allowAdmin: bool = False):
        if self.safetyManager is None:
            return None
        return self.safetyManager.canExecute(request, tool=tool, confirmed=confirmed, allowAdmin=allowAdmin)

    def enforce(self, request, tool=None, confirmed: bool = False, allowAdmin: bool = False):
        decision = self.canExecute(request, tool=tool, confirmed=confirmed, allowAdmin=allowAdmin)
        if decision is None:
            return None
        if not decision.canExecute():
            raise PermissionError(decision.reason or "Execution denied.")
        return decision

