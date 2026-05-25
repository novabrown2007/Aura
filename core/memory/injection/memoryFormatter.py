"""Category-aware memory formatting for prompt injection."""

from __future__ import annotations

from core.memory.models import Memory
from core.memory.injection.contextCompressor import ContextCompressor


class MemoryFormatter:
    """Render memories as concise assistant-readable context lines."""

    categoryLabels = {
        "preferences": "Preference",
        "projects": "Project",
        "people": "Person",
        "locations": "Location",
        "tasks": "Task",
        "conversation_summaries": "Recent summary",
        "system_context": "System context",
        "assistant_context": "Assistant context",
        "habits": "Habit",
        "reminders": "Reminder",
    }

    def __init__(self, compressor: ContextCompressor, context=None):
        self.compressor = compressor
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Formatter") if logger else None

    def formatMemory(self, memory: Memory, maxCharacters: int = 220) -> str:
        """Format one memory as a compact bullet body."""

        label = self.categoryLabels.get(memory.category, memory.category.replace("_", " ").title())
        content = self.compressor.compress(memory.content, maxCharacters=maxCharacters)
        if memory.category == "conversation_summaries":
            return f"{label}: {content}"
        if memory.title and memory.title.lower() not in content.lower():
            return f"{label} - {memory.title}: {content}"
        return f"{label}: {content}"

    def formatSection(self, lines: list[str]) -> str:
        """Return a complete Relevant Context section."""

        if not lines:
            return ""
        bullets = [f"- {line}" for line in lines if line.strip()]
        return "Relevant Context:\n" + "\n".join(bullets)

