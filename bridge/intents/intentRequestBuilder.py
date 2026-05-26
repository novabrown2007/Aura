"""Build assistant.intent requests for the Aura Protocol."""

from __future__ import annotations

from typing import Any

from ..protocol.auraCategories import AuraCategories
from ..protocol.auraMessage import AuraMessage


class IntentRequestBuilder:
    """Convert structured intents into assistant.intent protocol messages."""

    def __init__(self, context, sessionManager):
        self.context = context
        self.sessionManager = sessionManager

    def buildIntentRequest(
        self,
        intent: Any,
        sessionId: str | None = None,
        interface: str = "desktop",
        confidence: float | None = None,
        extraContext: dict[str, Any] | None = None,
    ) -> AuraMessage:
        """Build one assistant.intent message."""

        if isinstance(intent, dict):
            intentName = str(intent.get("intent") or intent.get("name") or "").strip()
            arguments = intent.get("arguments", {})
            response = str(intent.get("response") or "")
            confidence = confidence if confidence is not None else intent.get("confidence", 1.0)
        else:
            intentName = str(getattr(intent, "intent", None) or getattr(intent, "name", None) or "").strip()
            arguments = getattr(intent, "arguments", {})
            response = str(getattr(intent, "response", "") or "")
            confidence = confidence if confidence is not None else getattr(intent, "confidence", 1.0)

        if not isinstance(arguments, dict):
            arguments = {}

        session = self.sessionManager.getSession(sessionId) or self.sessionManager.createSession(interface=interface, sessionId=sessionId)
        context = self.sessionManager.buildContext(interface=interface, sessionId=session.sessionId, extra=extraContext or {})
        data = {
            "intent": intentName,
            "confidence": float(confidence if confidence is not None else 1.0),
            "arguments": arguments,
        }
        if response:
            data["response"] = response
        return AuraMessage(
            category=AuraCategories.ASSISTANT_INTENT,
            context=context,
            data=data,
            source={"system": "aura"},
            requestId=str(extraContext.get("requestId")) if extraContext and extraContext.get("requestId") else "",
        )

    def buildContextRequest(
        self,
        sessionId: str | None = None,
        interface: str = "desktop",
        contextData: dict[str, Any] | None = None,
    ) -> AuraMessage:
        """Build one assistant.context message."""

        session = self.sessionManager.getSession(sessionId) or self.sessionManager.createSession(interface=interface, sessionId=sessionId)
        context = self.sessionManager.buildContext(interface=interface, sessionId=session.sessionId, extra=contextData or {})
        return AuraMessage(
            category=AuraCategories.ASSISTANT_CONTEXT,
            context=context,
            data=contextData or {},
            source={"system": "aura"},
        )
