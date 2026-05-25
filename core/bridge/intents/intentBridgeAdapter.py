"""Assistant-side adapter that submits intents through the bridge client."""

from __future__ import annotations

from typing import Any

from ..protocol.auraCategories import AuraCategories


class IntentBridgeAdapter:
    """Convert Aura intents into assistant.intent bridge requests."""

    def __init__(self, context, bridgeClient, requestBuilder, validator=None):
        self.context = context
        self.bridgeClient = bridgeClient
        self.requestBuilder = requestBuilder
        self.validator = validator
        self.logger = context.logger.getChild("Bridge.Intent") if getattr(context, "logger", None) else None

    def submitIntent(
        self,
        intent: Any,
        sessionId: str | None = None,
        interface: str = "desktop",
        extraContext: dict[str, Any] | None = None,
    ):
        """Send one structured intent to the bridge."""

        message = self.requestBuilder.buildIntentRequest(
            intent,
            sessionId=sessionId,
            interface=interface,
            extraContext=extraContext,
        )
        return self.bridgeClient.sendMessage(message)

    def submitIntents(
        self,
        intents: list[Any],
        sessionId: str | None = None,
        interface: str = "desktop",
        extraContext: dict[str, Any] | None = None,
    ):
        """Send an ordered list of intents to the bridge."""

        results = []
        for intent in intents:
            results.append(self.submitIntent(intent, sessionId=sessionId, interface=interface, extraContext=extraContext))
        return results

