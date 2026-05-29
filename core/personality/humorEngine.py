"""Controlled lightweight humor for Aura."""

from __future__ import annotations

import re

from core.personality.models import HumorResponse


class HumorEngine:
    """Generate occasional deterministic humor without interrupting tasks."""

    def __init__(self, profile, logger=None):
        self.profile = profile
        self.logger = logger
        self.turnCounter = 0

    def maybeGenerate(self, userInput: str, responseText: str, interactionContext) -> HumorResponse:
        """Return a safe humorous aside when conditions are suitable."""

        if not self.profile.humorEnabled or self.profile.personalityStrength <= 0:
            return HumorResponse(reason="disabled")
        self.turnCounter += 1
        if self.turnCounter % self._interval() != 0:
            return HumorResponse(reason="interval")
        text = str(userInput or "").lower()
        if any(word in text for word in ("error", "stack trace", "traceback", "compile", "build failed")):
            return HumorResponse("That stack trace looks personally offended.", True, "developer_context")
        if any(word in text for word in ("slow", "taking forever", "compile time")):
            return HumorResponse("That wait time is making a strong case for geological classification.", True, "slow_context")
        if re.search(r"\bthanks|thank you\b", text):
            return HumorResponse("Anytime. I will keep the confetti virtual.", True, "thanks")
        return HumorResponse(reason="no_context")

    def _interval(self) -> int:
        """Return deterministic humor interval based on personality strength."""

        strength = max(0.0, min(1.0, float(self.profile.personalityStrength)))
        return max(3, int(round(9 - (strength * 4))))

