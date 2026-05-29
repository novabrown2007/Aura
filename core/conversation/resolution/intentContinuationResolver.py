"""Intent continuation and contextual modification resolver."""

from __future__ import annotations

import re

from core.conversation.conversationContext import ConversationContext


class IntentContinuationResolver:
    """Turn short follow-up modifications into explicit requests."""

    continuationWords = {"actually", "and", "also", "too", "instead", "make", "set", "dim", "brighten"}

    def isContinuation(self, text: str, context: ConversationContext) -> bool:
        lowered = str(text or "").strip().lower()
        if not lowered or context.activeEntity() is None:
            return False
        if re.match(r"^(actually|and|also|too|instead)\b", lowered):
            return True
        if re.match(r"^(make|set|dim|brighten|turn)\b", lowered) and not self._hasExplicitEntity(lowered):
            return True
        return False

    def resolve(self, text: str, context: ConversationContext) -> str:
        entity = context.activeEntity()
        topic = context.activeTopic()
        if entity is None:
            return text

        cleaned = str(text or "").strip()
        lowered = cleaned.lower()
        target = entity.name

        if re.match(r"^(actually|and|also|too|instead)\b", lowered):
            cleaned = re.sub(r"^(actually|and|also|too|instead)\s+", "", cleaned, flags=re.IGNORECASE).strip()
            lowered = cleaned.lower()

        if topic and topic.name == "lighting":
            if re.search(r"\bblue|red|green|purple|white|warm|cool\b", lowered):
                value = self._removeTargetWords(cleaned, target)
                value = re.sub(r"^(make|set|turn)\s+", "", value, flags=re.IGNORECASE).strip(" .")
                return f"Set {target} to {value}."
            if re.search(r"\bdim\b|\blow(er)?\b|\bmore\b", lowered):
                value = self._removeTargetWords(cleaned, target)
                value = re.sub(r"^dim\s+", "", value, flags=re.IGNORECASE).strip(" .")
                return f"Dim {target} {value}."
            if re.search(r"\bbrighten|brighter|up\b", lowered):
                value = self._removeTargetWords(cleaned, target)
                value = re.sub(r"^brighten\s+", "", value, flags=re.IGNORECASE).strip(" .")
                return f"Brighten {target} {value}."
            if re.search(r"\boff\b", lowered):
                return f"Turn off {target}."
            if re.search(r"\bon\b", lowered):
                return f"Turn on {target}."

        if topic and topic.name == "music":
            if re.search(r"\bdown|lower|quieter\b", lowered):
                return f"Turn down {target}."
            if re.search(r"\bup|louder\b", lowered):
                return f"Turn up {target}."

        return f"{cleaned} {target}".strip()

    @staticmethod
    def _removeTargetWords(text: str, target: str) -> str:
        result = str(text or "")
        result = re.sub(rf"\b{re.escape(target)}\b", "", result, flags=re.IGNORECASE)
        return " ".join(result.split())

    @staticmethod
    def _hasExplicitEntity(text: str) -> bool:
        return bool(re.search(r"\b(lights?|lamps?|music|playlist|calendar|event|email|weather)\b", text))
