"""Contextual suggestion generation for Aura."""

from __future__ import annotations

import re
from time import time

from core.personality.models import Suggestion


class SuggestionEngine:
    """Generate lightweight optional suggestions with memory-safe phrasing."""

    def __init__(self, context=None, profile=None, logger=None):
        self.context = context
        self.profile = profile
        self.logger = logger
        self.lastSuggestionAt = 0.0
        self.cooldownSeconds = 600.0
        self.lastSuggestion: Suggestion | None = None

    def maybeSuggest(self, userInput: str, responseText: str, interactionContext) -> Suggestion | None:
        """Return a contextual suggestion if throttling and policy allow it."""

        if not self.profile or not self.profile.suggestionsEnabled:
            return None
        if not self._passesThrottle(interactionContext):
            return None
        suggestion = self._fromContext(userInput, responseText)
        if suggestion is None:
            return None
        self.lastSuggestionAt = time()
        self.lastSuggestion = suggestion
        interactionContext.recordSuggestion()
        if self.logger:
            self.logger.info(f"Generated personality suggestion: {suggestion.category}")
        return suggestion

    def _passesThrottle(self, interactionContext) -> bool:
        now = time()
        if now - self.lastSuggestionAt < self.cooldownSeconds:
            if self.logger:
                self.logger.debug("Suggestion throttled by cooldown.")
            return False
        limit = max(0, int(self.profile.maxSuggestionsPerHour))
        if interactionContext.suggestionsInLastHour() >= limit:
            if self.logger:
                self.logger.debug("Suggestion throttled by hourly limit.")
            return False
        return True

    def _fromContext(self, userInput: str, responseText: str) -> Suggestion | None:
        text = str(userInput or "").lower()
        response = str(responseText or "").lower()
        if re.search(r"\b(code|coding|debug|compile|build|traceback|stack trace)\b", text):
            return Suggestion(
                "Want me to keep an eye out for related errors while you work through it?",
                reason="developer workflow context",
                category="workflow",
                priority=0.55,
            )
        if re.search(r"\b(reminder|calendar|schedule|meeting)\b", text + " " + response):
            return Suggestion(
                "Want me to add a reminder around that so it does not get lost?",
                reason="planning context",
                category="reminder",
                priority=0.5,
            )
        if self._memorySuggestsMusic() and re.search(r"\b(coding|work|focus)\b", text):
            return Suggestion(
                "You usually like music while focusing. Want me to open Spotify?",
                reason="recurring workflow preference",
                category="habit",
                priority=0.45,
            )
        return None

    def _memorySuggestsMusic(self) -> bool:
        memory = getattr(self.context, "memoryManager", None)
        if memory is None or not hasattr(memory, "getMemory"):
            return False
        try:
            data = memory.getMemory() or {}
        except Exception:
            return False
        text = " ".join(str(value) for value in data.values()).lower() if isinstance(data, dict) else str(data).lower()
        return "spotify" in text or "music while" in text or "music when" in text

