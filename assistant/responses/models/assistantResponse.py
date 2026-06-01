"""Canonical structured assistant response for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from assistant.responses.models.responseAction import ResponseAction
from assistant.responses.models.responseContext import ResponseContext
from assistant.responses.models.responseFollowup import ResponseFollowup
from assistant.responses.models.responseMetadata import ResponseMetadata
from assistant.responses.models.responseNotification import ResponseNotification


@dataclass
class AssistantResponse:
    """Canonical multimodal assistant response packet."""

    responseId: str = field(default_factory=lambda: uuid4().hex)
    spokenText: str = ""
    uiText: str = ""
    notifications: list[ResponseNotification] = field(default_factory=list)
    actions: list[ResponseAction] = field(default_factory=list)
    metadata: ResponseMetadata = field(default_factory=ResponseMetadata)
    followups: list[ResponseFollowup] = field(default_factory=list)
    context: ResponseContext = field(default_factory=ResponseContext)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    priority: str = "NORMAL"
    requiresAcknowledgement: bool = False

    def asDict(self) -> dict[str, Any]:
        return {
            "responseId": self.responseId,
            "spokenText": self.spokenText,
            "uiText": self.uiText,
            "notifications": [notification.asDict() for notification in self.notifications],
            "actions": [action.asDict() for action in self.actions],
            "metadata": self.metadata.asDict() if hasattr(self.metadata, "asDict") else dict(self.metadata or {}),
            "followups": [followup.asDict() for followup in self.followups],
            "context": self.context.asDict() if hasattr(self.context, "asDict") else dict(self.context or {}),
            "timestamp": self.timestamp,
            "priority": self.priority,
            "requiresAcknowledgement": bool(self.requiresAcknowledgement),
        }

    def __str__(self) -> str:
        return self.spokenText or self.uiText or ""

    @classmethod
    def fromDict(cls, values: dict[str, Any]):
        """Create a structured response from a dictionary payload."""

        metadata = values.get("metadata") or {}
        context = values.get("context") or {}
        return cls(
            responseId=str(values.get("responseId") or values.get("id") or uuid4().hex),
            spokenText=str(values.get("spokenText") or values.get("speechText") or values.get("text") or ""),
            uiText=str(values.get("uiText") or values.get("displayText") or values.get("text") or ""),
            notifications=[
                item if isinstance(item, ResponseNotification) else ResponseNotification(**dict(item))
                for item in list(values.get("notifications") or [])
            ],
            actions=[
                item if isinstance(item, ResponseAction) else ResponseAction(**dict(item))
                for item in list(values.get("actions") or [])
            ],
            metadata=metadata if isinstance(metadata, ResponseMetadata) else ResponseMetadata(**dict(metadata)),
            followups=[
                item if isinstance(item, ResponseFollowup) else ResponseFollowup(**dict(item))
                for item in list(values.get("followups") or [])
            ],
            context=context if isinstance(context, ResponseContext) else ResponseContext(**dict(context)),
            timestamp=str(values.get("timestamp") or datetime.utcnow().isoformat(timespec="seconds")),
            priority=str(values.get("priority") or "NORMAL"),
            requiresAcknowledgement=bool(values.get("requiresAcknowledgement", False)),
        )
