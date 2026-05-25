"""Conversation summarization and deterministic fact extraction."""

from __future__ import annotations

import re

from auraassistant.core.memory.models import MemorySummary


class MemorySummarizer:
    """Create compact, persistent summaries instead of storing endless transcripts."""

    def __init__(self, context=None, summaryLength: int = 280):
        self.context = context
        self.summaryLength = int(summaryLength or 280)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Summarizer") if logger else None

    def summarizeConversation(self, messages: list[tuple[str, str]] | list[dict], sessionId: str = "") -> MemorySummary | None:
        """Summarize a conversation deterministically."""

        normalized = self._normalizeMessages(messages)
        userMessages = [content for role, content in normalized if role == "user" and content]
        if not userMessages:
            return None

        facts = self.extractImportantFacts(normalized)
        joined = " ".join(userMessages)
        summary = self._compact(joined)
        tags = self._extractTags(summary + " " + " ".join(facts))
        result = MemorySummary(summary=summary, facts=facts, tags=tags, sessionId=sessionId)
        if self.logger:
            self.logger.info("Conversation summarized for memory storage")
        return result

    def extractImportantFacts(self, messages: list[tuple[str, str]] | list[dict]) -> list[str]:
        """Extract simple durable facts from user messages."""

        facts = []
        for role, content in self._normalizeMessages(messages):
            if role != "user":
                continue
            category = self.categorizeText(content)
            if category:
                facts.append(self._compact(content, limit=180))
        return facts[:8]

    def categorizeText(self, text: str) -> str | None:
        """Infer a memory category from text using deterministic cues."""

        lowered = str(text or "").lower()
        if self._looksSensitive(lowered):
            return None
        if re.search(r"\bi prefer\b|\bi like\b|\bi dislike\b|\bmy favorite\b|\bplease always\b|\bplease never\b", lowered):
            return "preferences"
        if re.search(r"\bi'?m working on\b|\bproject\b|\bpipeline\b|\bbuilding\b|\bimplementing\b", lowered):
            return "projects"
        if re.search(r"\bmy (friend|partner|manager|coworker|mom|dad|mother|father)\b|\bname is\b", lowered):
            return "people"
        if re.search(r"\bi live in\b|\bi am in\b|\blocation\b|\bhome\b|\boffice\b", lowered):
            return "locations"
        if re.search(r"\bremind me\b|\bremember to\b|\bneed to\b|\btodo\b|\btask\b", lowered):
            return "tasks"
        if re.search(r"\bevery day\b|\busually\b|\boften\b|\bevery morning\b|\bevery night\b", lowered):
            return "habits"
        return None

    def _compact(self, text: str, limit: int | None = None) -> str:
        limit = int(limit or self.summaryLength)
        cleaned = " ".join(str(text or "").split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(limit - 3, 0)].rstrip() + "..."

    @staticmethod
    def _extractTags(text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", str(text or "").lower())
        stop = {"the", "and", "for", "with", "that", "this", "from", "working", "prefer", "please"}
        return sorted({word for word in words if word not in stop})[:10]

    @staticmethod
    def _looksSensitive(text: str) -> bool:
        sensitive = ("password", "token", "api key", "secret", "credential", "private key")
        return any(term in text for term in sensitive)

    @staticmethod
    def _normalizeMessages(messages) -> list[tuple[str, str]]:
        normalized = []
        for message in messages or []:
            if isinstance(message, dict):
                role = str(message.get("role") or message.get("author") or "user").lower()
                content = str(message.get("content") or message.get("text") or "")
            else:
                role, content = message
                role = str(role).lower()
                content = str(content)
            role = "aura" if role in {"assistant", "aura"} else "user"
            normalized.append((role, content.strip()))
        return normalized

