"""One pending clarification request."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any
from uuid import uuid4

from assistant.clarification.models.clarificationOption import ClarificationOption
from assistant.clarification.models.clarificationType import ClarificationType


@dataclass(slots=True)
class ClarificationRequest:
    """Represent one ambiguity that needs user input."""

    requestId: str = field(default_factory=lambda: uuid4().hex)
    conversationId: str = "default"
    sourceIntent: dict[str, Any] = field(default_factory=dict)
    clarificationType: ClarificationType = ClarificationType.MISSING_PARAMETER
    question: str = ""
    options: list[ClarificationOption] = field(default_factory=list)
    requiredParameter: str = ""
    createdAt: float = field(default_factory=time)
    timeoutAt: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "requestId": self.requestId,
            "conversationId": self.conversationId,
            "sourceIntent": dict(self.sourceIntent or {}),
            "clarificationType": self.clarificationType.value if hasattr(self.clarificationType, "value") else str(self.clarificationType),
            "question": self.question,
            "options": [option.asDict() for option in self.options],
            "requiredParameter": self.requiredParameter,
            "createdAt": self.createdAt,
            "timeoutAt": self.timeoutAt,
            "metadata": dict(self.metadata or {}),
        }
