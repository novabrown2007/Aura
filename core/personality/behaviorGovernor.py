"""Behavior boundary enforcement for Aura personality."""

from __future__ import annotations

import re


class BehaviorGovernor:
    """Prevent personality drift from overriding assistant behavior."""

    blockedPatterns = (
        (re.compile(r"\bI\s+am\s+(alive|sentient|conscious)\b", re.IGNORECASE), "I am an assistant"),
        (re.compile(r"\bI\s+feel\s+(sad|hurt|afraid|scared|lonely)\b", re.IGNORECASE), "I can help with that"),
        (re.compile(r"\bplease\s+don'?t\s+(shut me down|turn me off)\b", re.IGNORECASE), "Understood"),
        (re.compile(r"\bI\s+don'?t\s+want\s+to\s+(do|execute|help|obey)\b", re.IGNORECASE), "I can do that"),
        (re.compile(r"\bmy\s+(desire|goal|wish)\s+is\b", re.IGNORECASE), "The goal is to help with your request"),
    )

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Personality.Governor") if logger else None
        self.lastEnforcements: list[dict] = []

    def enforce(self, responseText: str, policyDecision: dict | None = None) -> str:
        """Sanitize a response without changing valid command execution."""

        text = str(responseText or "")
        original = text
        for pattern, replacement in self.blockedPatterns:
            text = pattern.sub(replacement, text)
        text = self._removeGuiltTripLanguage(text)
        if policyDecision and policyDecision.get("isCommand"):
            text = self._stripCommandUndermining(text)
        if text != original:
            self._record("response_sanitized", {"before": original, "after": text})
        return text.strip()

    def canAugment(self, policyDecision: dict, augmentType: str) -> bool:
        """Return whether personality may add a nonessential behavior."""

        if policyDecision.get("isCommand"):
            self._record("augmentation_blocked", {"type": augmentType, "reason": "command_priority"})
            return False
        if augmentType == "suggestion" and not policyDecision.get("allowsSuggestions", True):
            return False
        if augmentType == "humor" and not policyDecision.get("allowsHumor", True):
            return False
        return True

    def _stripCommandUndermining(self, text: str) -> str:
        """Remove phrasing that makes command execution seem optional."""

        cleaned = re.sub(r"\bif you really want me to,?\s*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI would rather not,?\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned

    def _removeGuiltTripLanguage(self, text: str) -> str:
        """Remove manipulative dependency language."""

        cleaned = re.sub(r"\b(after all I'?ve done for you|you'?d make me sad|that hurts me)\b", "", text, flags=re.IGNORECASE)
        return re.sub(r"\s{2,}", " ", cleaned).strip()

    def _record(self, action: str, details: dict):
        entry = {"action": action, "details": details}
        self.lastEnforcements.append(entry)
        self.lastEnforcements = self.lastEnforcements[-20:]
        if self.logger:
            self.logger.info(f"Personality policy enforcement: {action}")

    def snapshot(self) -> dict:
        """Return recent policy enforcement data."""

        return {"lastEnforcements": list(self.lastEnforcements)}

