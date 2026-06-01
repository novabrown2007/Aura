"""Resolve clarification replies into deterministic values."""

from __future__ import annotations

import re
from typing import Any

from assistant.clarification.models import ClarificationOption


class ClarificationResolver:
    """Map user replies onto one of the pending clarification options."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Resolver") if logger else None

    def resolve(self, session, userInput: str) -> dict[str, Any]:
        request = session.activeRequest
        requestData = request.asDict() if hasattr(request, "asDict") else dict(request or {})
        text = str(userInput or "").strip()
        options = self._options(requestData.get("options") or [])

        if not text:
            return {"resolved": False, "reason": "Empty response."}

        option = self._matchOption(text, options)
        if option is not None:
            return {
                "resolved": True,
                "value": option.value,
                "selectedOption": option.asDict(),
                "confidence": 1.0,
            }

        required = str(requestData.get("requiredParameter") or "").strip()
        if required:
            value = self._extractValue(required, text)
            if value is not None:
                return {
                    "resolved": True,
                    "value": value,
                    "selectedOption": None,
                    "confidence": 0.9,
                }

        if len(text.split()) <= 5:
            return {
                "resolved": True,
                "value": self._clean(text),
                "selectedOption": None,
                "confidence": 0.6,
            }

        return {"resolved": False, "reason": "Could not map the reply to one of the options."}

    def _matchOption(self, text: str, options: list[ClarificationOption]) -> ClarificationOption | None:
        normalized = self._clean(text)
        ordinal = self._ordinalIndex(normalized)
        if ordinal is not None and 0 <= ordinal < len(options):
            return options[ordinal]

        for option in options:
            label = self._clean(option.label)
            value = self._clean(str(option.value))
            description = self._clean(option.description)
            if normalized == label or normalized == value:
                return option
            if label and label in normalized:
                return option
            if value and value in normalized:
                return option
            if description and description in normalized:
                return option
        return None

    @staticmethod
    def _options(values) -> list[ClarificationOption]:
        options = []
        for value in list(values or []):
            if isinstance(value, ClarificationOption):
                options.append(value)
                continue
            payload = dict(value or {})
            options.append(
                ClarificationOption(
                    optionId=str(payload.get("optionId") or payload.get("id") or ""),
                    label=str(payload.get("label") or ""),
                    value=payload.get("value", payload.get("label")),
                    description=str(payload.get("description") or ""),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return options

    @staticmethod
    def _ordinalIndex(text: str) -> int | None:
        words = {
            "first": 0,
            "1st": 0,
            "one": 0,
            "second": 1,
            "2nd": 1,
            "two": 1,
            "third": 2,
            "3rd": 2,
            "three": 2,
            "fourth": 3,
            "4th": 3,
            "five": 4,
        }
        for key, index in words.items():
            if re.search(rf"\b{re.escape(key)}\b", text):
                return index
        match = re.search(r"\boption\s*(\d+)\b", text)
        if match:
            return max(int(match.group(1)) - 1, 0)
        match = re.search(r"\b(\d+)\b", text)
        if match:
            return max(int(match.group(1)) - 1, 0)
        return None

    @staticmethod
    def _extractValue(parameter: str, text: str) -> Any | None:
        normalized = ClarificationResolver._clean(text)
        if parameter in {"time", "start_time", "due_time"}:
            match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", normalized)
            if match:
                return text.strip()
        if parameter in {"room", "location", "account"}:
            return normalized
        return normalized if normalized else None

    @staticmethod
    def _clean(text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9\s]+", " ", str(text or "").lower())
        return " ".join(cleaned.split()).strip()
