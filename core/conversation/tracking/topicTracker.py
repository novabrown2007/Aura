"""Topic tracking for short-term conversation continuity."""

from __future__ import annotations

import re
from time import time

from core.conversation.models import ActiveTopic


class TopicTracker:
    """Infer active conversation topic from text or tool intents."""

    topicPatterns = {
        "lighting": r"\b(lights?|lamps?|brightness|dim|brighten|blue|red|green|color)\b",
        "music": r"\b(music|song|playlist|spotify|jazz|volume|play|pause)\b",
        "calendar": r"\b(calendar|event|meeting|appointment|schedule|remind|reminder)\b",
        "email": r"\b(email|mail|draft|message|send)\b",
        "weather": r"\b(weather|forecast|temperature|rain|snow)\b",
    }

    def extract(self, text: str) -> ActiveTopic | None:
        lowered = str(text or "").lower()
        for topic, pattern in self.topicPatterns.items():
            if re.search(pattern, lowered):
                return self._topic(topic)
        return None

    def fromIntent(self, intent: str) -> ActiveTopic | None:
        lowered = str(intent or "").lower()
        if "light" in lowered:
            return self._topic("lighting")
        if "calendar" in lowered or "reminder" in lowered:
            return self._topic("calendar")
        if "email" in lowered:
            return self._topic("email")
        if "music" in lowered or "media" in lowered:
            return self._topic("music")
        return None

    @staticmethod
    def _topic(name: str) -> ActiveTopic:
        now = time()
        return ActiveTopic(name=name, createdAt=now, updatedAt=now)

