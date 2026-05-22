"""Canonical Aura Protocol categories."""

from __future__ import annotations


class AuraCategories:
    """Stable category names used by the Aura Protocol."""

    ASSISTANT_NOTIFICATION = "assistant.notification"
    ASSISTANT_RESPONSE = "assistant.response"
    ASSISTANT_ERROR = "assistant.error"
    ASSISTANT_STREAM_AVAILABLE = "assistant.stream.available"
    ASSISTANT_INTENT = "assistant.intent"
    ASSISTANT_CONTEXT = "assistant.context"
    ANALYSIS_RESULT = "analysis.result"

    ALL = (
        ASSISTANT_NOTIFICATION,
        ASSISTANT_RESPONSE,
        ASSISTANT_ERROR,
        ASSISTANT_STREAM_AVAILABLE,
        ASSISTANT_INTENT,
        ASSISTANT_CONTEXT,
        ANALYSIS_RESULT,
    )

    @classmethod
    def isKnown(cls, category: str) -> bool:
        """Return whether a category is a recognized Aura category."""

        return str(category) in cls.ALL

