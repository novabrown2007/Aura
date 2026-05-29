"""Initiative throttling and appropriateness decisions."""

from __future__ import annotations


class InitiativeManager:
    """Decide when proactive behavior is useful enough to show."""

    def __init__(self, profile, logger=None):
        self.profile = profile
        self.logger = logger
        self.evaluationCount = 0
        self.lastDecision = {}

    def shouldOffer(self, interactionContext, policyDecision: dict) -> bool:
        """Return whether Aura may add a proactive suggestion."""

        self.evaluationCount += 1
        allowed = (
            self.profile.personalityEnabled
            and self.profile.suggestionsEnabled
            and self.profile.initiativeLevel > 0
            and not policyDecision.get("isCommand")
            and interactionContext.conversationIntensity < 0.85
        )
        self.lastDecision = {
            "allowed": bool(allowed),
            "initiativeLevel": self.profile.initiativeLevel,
            "policyPriority": policyDecision.get("priority"),
        }
        if self.logger:
            self.logger.debug(f"Initiative evaluated: {self.lastDecision}")
        return bool(allowed)

    def snapshot(self) -> dict:
        return {"evaluationCount": self.evaluationCount, "lastDecision": dict(self.lastDecision)}

