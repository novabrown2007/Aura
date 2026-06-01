"""Module-specific clarification strategies."""

from __future__ import annotations

from assistant.clarification.models import ClarificationOption


class ModuleClarificationStrategy:
    """Support module-provided clarification choices."""

    @staticmethod
    def buildQuestion(sourceIntent: dict | None = None, options: list[ClarificationOption] | None = None) -> str:
        if options:
            return "Which one should I use?"
        intentName = str((sourceIntent or {}).get("intent") or "").lower()
        if "spotify" in intentName:
            return "Which playlist would you like?"
        if "email" in intentName:
            return "Which draft should I use?"
        return "Which one would you like?"
