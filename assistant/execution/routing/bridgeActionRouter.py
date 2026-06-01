"""Route bridge/device actions."""

from __future__ import annotations


class BridgeActionRouter:
    """Execute bridge-owned actions through the bridge client if present."""

    def __init__(self, context=None):
        self.context = context

    def route(self, request, actionDefinition, confirmed: bool = False, allowAdmin: bool = False):
        bridge = getattr(self.context, "bridgeClient", None) or getattr(self.context, "auraBridgeClient", None) or getattr(self.context, "bridgeRouter", None)
        if bridge is None:
            raise RuntimeError("Bridge client unavailable.")
        actionName = str(getattr(actionDefinition, "actionName", "") or "")
        payload = dict(getattr(request, "parameters", {}) or {})
        for methodName in ("executeAction", "runAction", "dispatch", "sendAction"):
            if hasattr(bridge, methodName):
                return getattr(bridge, methodName)(actionName, payload)
        raise RuntimeError("Bridge action router unavailable.")
