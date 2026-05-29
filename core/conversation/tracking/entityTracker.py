"""Entity extraction and tracking for conversation continuity."""

from __future__ import annotations

import re
from time import time
from typing import Any

from core.conversation.models import ActiveEntity


class EntityTracker:
    """Extract active entities from user text and executed actions."""

    def extract(self, text: str, topic: str = "") -> list[ActiveEntity]:
        lowered = str(text or "").lower()
        entities: list[ActiveEntity] = []
        lightMatch = re.search(r"\b(?:the|my)?\s*([a-z][a-z0-9 _-]{0,40}?)\s+(lights?|lamps?)\b", lowered)
        if lightMatch:
            room = self._cleanRoom(lightMatch.group(1))
            name = f"{room} lights" if room else "lights"
            entities.append(self._entity(name, "light", "lighting", {"room": room} if room else {}))
        elif re.search(r"\blights?|lamps?\b", lowered):
            entities.append(self._entity("lights", "light", "lighting"))

        if re.search(r"\b(music|song|playlist|spotify|jazz|volume|playback)\b", lowered):
            name = "music playback"
            if "playlist" in lowered:
                name = "playlist"
            entities.append(self._entity(name, "media", "music"))

        if re.search(r"\b(calendar|event|meeting|appointment)\b", lowered):
            entities.append(self._entity("calendar event", "calendar_event", "calendar"))

        if re.search(r"\b(email|draft|message)\b", lowered):
            entities.append(self._entity("email draft", "email", "email"))

        if re.search(r"\b(weather|forecast|temperature)\b", lowered):
            entities.append(self._entity("weather", "weather", "weather"))

        if topic and entities:
            for entity in entities:
                entity.topic = entity.topic or topic
        return entities

    def fromAction(self, intent: str, arguments: dict[str, Any]) -> list[ActiveEntity]:
        topic = self._topicFromIntent(intent)
        if topic == "lighting":
            room = str((arguments or {}).get("room") or "").strip().lower()
            name = f"{room} lights" if room else "lights"
            return [self._entity(name, "light", "lighting", {"room": room} if room else {})]
        text = f"{intent} " + " ".join(str(value) for value in (arguments or {}).values())
        entities = self.extract(text)
        if entities:
            return entities
        return []

    @staticmethod
    def _entity(name: str, entityType: str, topic: str, attributes: dict[str, Any] | None = None) -> ActiveEntity:
        now = time()
        return ActiveEntity(
            name=name.strip(),
            entityType=entityType,
            topic=topic,
            attributes=attributes or {},
            createdAt=now,
            updatedAt=now,
        )

    @staticmethod
    def _cleanRoom(value: str) -> str:
        ignored = {"turn", "set", "make", "dim", "brighten", "off", "on", "the", "my", "a", "an"}
        words = [word for word in str(value or "").split() if word not in ignored]
        return " ".join(words).strip()

    @staticmethod
    def _topicFromIntent(intent: str) -> str:
        lowered = str(intent or "").lower()
        if "light" in lowered:
            return "lighting"
        if "calendar" in lowered or "reminder" in lowered:
            return "calendar"
        if "email" in lowered:
            return "email"
        return ""
