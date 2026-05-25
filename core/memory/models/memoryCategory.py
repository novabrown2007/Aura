"""Structured long-term memory categories for Aura."""

from __future__ import annotations

from enum import Enum


class MemoryCategory(str, Enum):
    """Allowed categories for every persisted Aura memory."""

    PREFERENCES = "preferences"
    PROJECTS = "projects"
    PEOPLE = "people"
    LOCATIONS = "locations"
    TASKS = "tasks"
    CONVERSATION_SUMMARIES = "conversation_summaries"
    SYSTEM_CONTEXT = "system_context"
    ASSISTANT_CONTEXT = "assistant_context"
    HABITS = "habits"
    REMINDERS = "reminders"

    @classmethod
    def values(cls) -> list[str]:
        """Return category values in stable order."""

        return [category.value for category in cls]

    @classmethod
    def normalize(cls, category: str | "MemoryCategory") -> str:
        """Validate and normalize a category value."""

        value = category.value if isinstance(category, cls) else str(category or "").strip().lower()
        if value not in cls.values():
            raise ValueError(f"Invalid memory category: {category}")
        return value

