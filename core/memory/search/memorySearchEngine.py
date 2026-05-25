"""Deterministic keyword search for structured Aura memories."""

from __future__ import annotations

from difflib import SequenceMatcher

from core.memory.models import Memory, MemoryQuery


class MemorySearchEngine:
    """Lightweight search over title, content, tags, and category."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Search") if logger else None

    def search(self, memories: list[Memory], query: MemoryQuery) -> list[Memory]:
        """Return memories ranked by deterministic lexical relevance."""

        tokens = self._tokenize(query.keywords)
        tags = set(query.normalizedTags())
        ranked = []

        for memory in memories:
            score = self.scoreMemory(memory, tokens, tags)
            if tokens or tags:
                if score <= 0:
                    continue
            ranked.append((score, memory.importance, memory.updatedAt, memory))

        ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        results = [item[3] for item in ranked]
        if self.logger:
            self.logger.debug(f"Memory search returned {len(results)} result(s)")
        return results[: query.limit] if query.limit else results

    def scoreMemory(self, memory: Memory, tokens: set[str], tags: set[str] | None = None) -> float:
        """Score one memory with exact, partial, tag, and category matches."""

        tags = tags or set()
        haystack = self._tokenize(f"{memory.category} {memory.title} {memory.content} {' '.join(memory.tags)}")
        score = 0.0
        for token in tokens:
            if token in haystack:
                score += 2.0
                continue
            if any(self._fuzzy(token, candidate) >= 0.82 for candidate in haystack):
                score += 0.75
        score += len(tags.intersection(memory.tags)) * 2.5
        return score

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text or ""))
        return {token for token in cleaned.split() if len(token) > 1}

    @staticmethod
    def _fuzzy(left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

