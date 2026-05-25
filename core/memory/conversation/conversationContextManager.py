"""Short-term conversation context tracking for memory retrieval."""

from __future__ import annotations

import re
from collections import deque


class ConversationContextManager:
    """Track active conversational focus separately from long-term memory."""

    def __init__(self, context=None, maxTurns: int = 8):
        self.context = context
        self.maxTurns = int(maxTurns)
        self.turns = deque(maxlen=self.maxTurns)
        self.activeTopics: list[str] = []
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.ConversationContext") if logger else None

    def recordTurn(self, role: str, content: str):
        """Record one short-term conversational turn."""

        content = str(content or "").strip()
        if not content:
            return
        self.turns.append((str(role or "user"), content))
        self.activeTopics = self._extractTopics(" ".join(item[1] for item in self.turns))

    def buildContext(self, userMessage: str, conversationHistory: list | None = None) -> dict:
        """Return short-term context used to score long-term memories."""

        if conversationHistory:
            for message in conversationHistory[-self.maxTurns:]:
                if isinstance(message, dict):
                    role = str(message.get("role") or message.get("author") or "user")
                    content = str(message.get("content") or "")
                else:
                    role, content = message
                self.recordTurn(role, content)
        self.recordTurn("user", userMessage)
        recentText = " ".join(content for _, content in self.turns)
        topics = self._extractTopics(f"{recentText} {userMessage}")
        self.activeTopics = topics
        return {
            "recentText": recentText,
            "activeTopics": topics,
            "recentTokens": self._tokenize(recentText),
            "messageTokens": self._tokenize(userMessage),
        }

    @staticmethod
    def _extractTopics(text: str) -> list[str]:
        stop = {
            "the", "and", "for", "with", "that", "this", "from", "have", "about",
            "still", "working", "please", "aura", "nova", "response", "assistant",
        }
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", str(text or "").lower())
        counts = {}
        for word in words:
            if word in stop:
                continue
            counts[word] = counts.get(word, 0) + 1
        return [
            word for word, _ in sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)[:12]
        ]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(ConversationContextManager._extractTopics(text))

