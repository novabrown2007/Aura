"""Parameter-level clarification strategies."""

from __future__ import annotations

from assistant.clarification.models import ClarificationType


class ParameterClarificationStrategy:
    """Generate natural parameter questions."""

    @staticmethod
    def buildQuestion(parameter: str, sourceIntent: dict | None = None) -> str:
        parameter = str(parameter or "").strip().lower()
        intentName = str((sourceIntent or {}).get("intent") or "").lower()
        if parameter == "room":
            return "Which room would you like me to use?"
        if parameter in {"playlist", "song", "track"}:
            return "Which playlist would you like?"
        if parameter in {"account", "email_account"}:
            return "Which account should I use?"
        if parameter in {"time", "start_time", "due_time"}:
            if "tomorrow" in intentName:
                return "What time tomorrow?"
            return "What time should I use?"
        if parameter in {"location", "place"}:
            return "Which location should I use?"
        return f"What {parameter} should I use?"

    @staticmethod
    def parameterType(parameter: str) -> ClarificationType:
        parameter = str(parameter or "").strip().lower()
        if parameter in {"time", "start_time", "due_time"}:
            return ClarificationType.TIME_SELECTION
        if parameter in {"location", "room", "place"}:
            return ClarificationType.LOCATION_SELECTION
        if parameter in {"account", "email_account"}:
            return ClarificationType.ACCOUNT_SELECTION
        return ClarificationType.MISSING_PARAMETER
