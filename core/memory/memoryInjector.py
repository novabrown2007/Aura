"""Prompt context injection for structured memories."""

from __future__ import annotations

from core.memory.models import Memory


class MemoryInjector:
    """Format relevant memories for prompt continuity."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Injector") if logger else None

    def buildContext(self, memories: list[Memory], maxItems: int = 8) -> dict[str, str]:
        """Return prompt-friendly category/title memory context."""

        context = {}
        for memory in memories[: int(maxItems)]:
            key = f"{memory.category}.{self._key(memory.title)}"
            context[key] = memory.content
        if self.logger:
            self.logger.debug(f"Built memory context with {len(context)} item(s)")
        return context

    def injectIntoPrompt(self, prompt: str, memories: list[Memory], maxItems: int = 8) -> str:
        """Append relevant memories to an existing system prompt."""

        context = self.buildContext(memories, maxItems=maxItems)
        if not context:
            return prompt
        lines = ["Relevant long-term memory:"]
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        if self.logger:
            self.logger.info(f"Injected {len(context)} memory item(s)")
        return f"{prompt.rstrip()}\n\n" + "\n".join(lines)

    @staticmethod
    def _key(title: str) -> str:
        cleaned = "".join(character.lower() if character.isalnum() else "_" for character in str(title or "memory"))
        return "_".join(part for part in cleaned.split("_") if part)[:64] or "memory"

