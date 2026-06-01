"""Ambiguity detection result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from assistant.clarification.models.clarificationOption import ClarificationOption
from assistant.clarification.models.clarificationType import ClarificationType


@dataclass(slots=True)
class AmbiguityResult:
    """Describe why clarification is required."""

    ambiguous: bool = False
    clarificationType: ClarificationType = ClarificationType.MISSING_PARAMETER
    reason: str = ""
    question: str = ""
    options: list[ClarificationOption] = field(default_factory=list)
    requiredParameter: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "ambiguous": bool(self.ambiguous),
            "clarificationType": self.clarificationType.value if hasattr(self.clarificationType, "value") else str(self.clarificationType),
            "reason": self.reason,
            "question": self.question,
            "options": [option.asDict() for option in self.options],
            "requiredParameter": self.requiredParameter,
            "confidence": float(self.confidence or 0.0),
            "metadata": dict(self.metadata or {}),
        }
