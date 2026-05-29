"""Pronoun resolution for short-term conversation context."""

from __future__ import annotations

import re

from core.conversation.conversationContext import ConversationContext


class PronounResolver:
    """Resolve lightweight references such as it, them, this, and that."""

    pronouns = {"it", "them", "that", "those", "this"}

    def hasPronoun(self, text: str) -> bool:
        tokens = set(re.findall(r"[a-z0-9']+", str(text or "").lower()))
        return bool(tokens & self.pronouns)

    def resolve(self, text: str, context: ConversationContext) -> tuple[str, dict[str, str]]:
        entity = context.activeEntity()
        if entity is None:
            return text, {}
        resolved = str(text or "")
        replacements: dict[str, str] = {}
        for pronoun in self.pronouns:
            pattern = rf"\b{re.escape(pronoun)}\b"
            if re.search(pattern, resolved, flags=re.IGNORECASE):
                resolved = re.sub(pattern, entity.name, resolved, flags=re.IGNORECASE)
                replacements[pronoun] = entity.name
        return resolved, replacements

