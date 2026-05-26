"""Validation helpers for Aura Protocol messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .protocol.auraCategories import AuraCategories


@dataclass(slots=True)
class AuraValidationError:
    """Structured validation error."""

    code: str
    message: str


class AuraValidator:
    """Validate Aura Protocol messages and payloads deterministically."""

    @classmethod
    def validateMessage(cls, message) -> tuple[bool, AuraValidationError | None]:
        """Validate the top-level message envelope."""

        if message is None:
            return False, AuraValidationError("MALFORMED_MESSAGE", "Message cannot be empty.")

        if isinstance(message, dict):
            category = str(message.get("category") or "")
            data = message.get("data")
            context = message.get("context")
            source = message.get("source")
        else:
            category = str(getattr(message, "category", "") or "")
            data = getattr(message, "data", None)
            context = getattr(message, "context", None)
            source = getattr(message, "source", None)

        if not category:
            return False, AuraValidationError("MALFORMED_MESSAGE", "Message category is required.")

        if not AuraCategories.isKnown(category) and not category.startswith("assistant."):
            return False, AuraValidationError("INVALID_CATEGORY", f"Unsupported category: {category}")

        for field_name, value in (("data", data), ("context", context), ("source", source)):
            if value is not None and not isinstance(value, dict):
                return False, AuraValidationError("MALFORMED_MESSAGE", f"{field_name} must be an object.")

        if category == AuraCategories.ASSISTANT_INTENT:
            return cls.validateIntent(data or {})
        if category == AuraCategories.ASSISTANT_CONTEXT:
            return cls.validateContext(data or {})
        if category == AuraCategories.ASSISTANT_STREAM_AVAILABLE:
            return cls.validateStream(data or {})
        if category == AuraCategories.ASSISTANT_NOTIFICATION:
            return cls.validateNotification(data or {})
        if category == AuraCategories.ASSISTANT_RESPONSE:
            return cls.validateResponse(data or {})
        if category == AuraCategories.ASSISTANT_ERROR:
            return cls.validateError(data or {})
        if category == AuraCategories.ANALYSIS_RESULT:
            return cls.validateAnalysis(data or {})

        return True, None

    @staticmethod
    def validateIntent(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate an assistant intent request."""

        intent = str(data.get("intent") or "").strip()
        if not intent:
            return False, AuraValidationError("INVALID_INTENT", "Intent name is required.")

        confidence = data.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return False, AuraValidationError("INVALID_INTENT", "Intent confidence must be numeric.")
        if not 0.0 <= confidence <= 1.0:
            return False, AuraValidationError("INVALID_INTENT", "Confidence must be between 0 and 1.")

        arguments = data.get("arguments", {})
        if arguments is not None and not isinstance(arguments, dict):
            return False, AuraValidationError("INVALID_INTENT", "Intent arguments must be an object.")

        return True, None

    @staticmethod
    def validateContext(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate assistant context sync payloads."""

        for key in ("sessionId", "interface"):
            if key in data and str(data.get(key) or "").strip() == "":
                return False, AuraValidationError("INVALID_CONTEXT", f"{key} cannot be empty.")
        return True, None

    @staticmethod
    def validateStream(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate stream metadata payloads."""

        stream_id = str(data.get("streamId") or "").strip()
        stream_type = str(data.get("streamType") or "").strip()
        if not stream_id:
            return False, AuraValidationError("INVALID_STREAM", "streamId is required.")
        if not stream_type:
            return False, AuraValidationError("INVALID_STREAM", "streamType is required.")
        return True, None

    @staticmethod
    def validateNotification(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate assistant notification payloads."""

        event = str(data.get("event") or "").strip()
        if not event and not data.get("title"):
            return False, AuraValidationError("INVALID_NOTIFICATION", "Notification event or title is required.")
        return True, None

    @staticmethod
    def validateResponse(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate assistant response payloads."""

        request_id = str(data.get("requestId") or "").strip()
        if not request_id:
            return False, AuraValidationError("INVALID_RESPONSE", "requestId is required.")
        return True, None

    @staticmethod
    def validateError(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate assistant error payloads."""

        code = str(data.get("code") or "").strip()
        message = str(data.get("message") or "").strip()
        if not code or not message:
            return False, AuraValidationError("INVALID_ERROR", "Error code and message are required.")
        return True, None

    @staticmethod
    def validateAnalysis(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate auxiliary analysis payloads."""

        if not isinstance(data, dict):
            return False, AuraValidationError("INVALID_ANALYSIS", "Analysis payload must be an object.")
        return True, None

    @classmethod
    def validateSubscription(cls, data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate subscription payloads."""

        categories = data.get("categories")
        if categories is None:
            category = str(data.get("category") or "").strip()
            if not category and not data.get("wildcard"):
                return False, AuraValidationError("INVALID_SUBSCRIPTION", "At least one category is required.")
            return True, None

        if not isinstance(categories, list) or not categories:
            return False, AuraValidationError("INVALID_SUBSCRIPTION", "categories must be a non-empty list.")
        if any(not str(category).strip() for category in categories):
            return False, AuraValidationError("INVALID_SUBSCRIPTION", "Subscription categories cannot be empty.")
        return True, None

    @staticmethod
    def validateSession(data: dict[str, Any]) -> tuple[bool, AuraValidationError | None]:
        """Validate session data."""

        session_id = str(data.get("sessionId") or "").strip()
        interface = str(data.get("interface") or "").strip()
        if not session_id:
            return False, AuraValidationError("INVALID_SESSION", "sessionId is required.")
        if not interface:
            return False, AuraValidationError("INVALID_SESSION", "interface is required.")
        return True, None
