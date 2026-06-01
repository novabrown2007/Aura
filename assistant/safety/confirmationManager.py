"""Confirmation tracking for Aura execution governance."""

from __future__ import annotations

from collections import OrderedDict

from assistant.safety.models import ConfirmationRequest


class ConfirmationManager:
    """Track pending confirmations and their resolution."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Confirmation") if logger else None
        self.pending: "OrderedDict[str, ConfirmationRequest]" = OrderedDict()

    def requestConfirmation(self, request, decision, prompt: str = "", timeoutSeconds: int = 60):
        confirmation = ConfirmationRequest(
            prompt=prompt or self._defaultPrompt(request),
            request=request.asDict() if hasattr(request, "asDict") else dict(request or {}),
            decision=decision.asDict() if hasattr(decision, "asDict") else dict(decision or {}),
            timeoutSeconds=timeoutSeconds,
        )
        self.pending[confirmation.requestId] = confirmation
        return confirmation

    def confirm(self, requestId: str, approved: bool = True):
        confirmation = self.pending.pop(str(requestId), None)
        if confirmation is None:
            return None
        confirmation.acknowledged = True
        payload = confirmation.asDict()
        payload["approved"] = bool(approved)
        payload["origin"] = "safety_manager"
        self._emit("confirmation.received", payload)
        return confirmation, bool(approved)

    def snapshot(self) -> dict:
        return {"pendingConfirmations": [confirmation.asDict() for confirmation in self.pending.values()]}

    def _defaultPrompt(self, request) -> str:
        action = str(getattr(request, "action", "") or "action")
        return f"Please confirm {action}."

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception:
            return None
