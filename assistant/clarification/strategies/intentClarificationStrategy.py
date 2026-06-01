"""Intent-level clarification strategies."""

from __future__ import annotations

from assistant.clarification.models import ClarificationOption, ClarificationType


class IntentClarificationStrategy:
    """Generate natural questions when the intent itself is unclear."""

    @staticmethod
    def buildQuestion(sourceIntent: dict, ambiguityType: ClarificationType, requiredParameter: str = "") -> str:
        intentName = str((sourceIntent or {}).get("intent") or "").lower()
        if ambiguityType == ClarificationType.LOW_CONFIDENCE:
            return "I want to make sure I understood that correctly. What should I do?"
        if ambiguityType == ClarificationType.MULTIPLE_OPTIONS:
            return "Which one should I use?"
        if "music" in intentName:
            return "Which playlist would you like?"
        if "email" in intentName:
            return "Which draft should I use?"
        if "schedule" in intentName or "calendar" in intentName:
            return "What time should I use?"
        if requiredParameter:
            return f"What {requiredParameter} would you like me to use?"
        return "Which one would you like me to use?"

    @staticmethod
    def buildOptions(labels: list[str]) -> list[ClarificationOption]:
        return [ClarificationOption(label=str(label), value=label, description=str(label)) for label in labels if str(label).strip()]
