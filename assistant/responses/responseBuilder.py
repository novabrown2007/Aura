"""Construct structured assistant responses from provider output."""

from __future__ import annotations

from datetime import datetime
from time import time
from typing import Any
from uuid import uuid4

from assistant.notifications.models import NotificationPriority
from assistant.responses.models import (
    AssistantResponse,
    ResponseAction,
    ResponseContext,
    ResponseFollowup,
    ResponseMetadata,
    ResponseNotification,
)


class ResponseBuilder:
    """Normalize raw provider output into structured response packets."""

    def __init__(self, context=None, contextManager=None):
        self.context = context
        self.contextManager = contextManager
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Builder") if logger else None

    def build(self, userInput: str, providerResponse=None, spokenText: str = "", uiText: str = "", metadata: dict | None = None):
        """Build a structured response from raw provider output."""

        providerPayload = self._providerPayload(providerResponse)
        structured = providerPayload if isinstance(providerPayload, dict) else {}
        responseText = (
            spokenText
            or uiText
            or str(structured.get("spokenText") or structured.get("uiText") or structured.get("response") or structured.get("text") or getattr(providerResponse, "text", "") or "")
        )
        response = AssistantResponse(
            responseId=str(structured.get("responseId") or uuid4().hex),
            spokenText=str(structured.get("spokenText") or responseText),
            uiText=str(structured.get("uiText") or responseText),
            notifications=self._buildNotifications(structured.get("notifications")),
            actions=self._buildActions(structured.get("actions")),
            metadata=self._buildMetadata(providerResponse, structured, metadata),
            followups=self._buildFollowups(structured.get("followups")),
            context=self._buildContext(userInput),
            timestamp=str(structured.get("timestamp") or datetime.utcnow().isoformat(timespec="seconds")),
            priority=str(structured.get("priority") or "NORMAL"),
            requiresAcknowledgement=bool(structured.get("requiresAcknowledgement", False)),
        )
        return response

    def fromText(self, userInput: str, text: str, providerResponse=None, metadata: dict | None = None):
        """Build a response from plain text output."""

        return self.build(userInput, providerResponse=providerResponse, spokenText=text, uiText=text, metadata=metadata)

    def _buildContext(self, userInput: str) -> ResponseContext:
        if self.contextManager is not None:
            return self.contextManager.buildContext(userInput)
        return ResponseContext(userInput=str(userInput or ""))

    @staticmethod
    def _providerPayload(providerResponse) -> dict[str, Any]:
        if providerResponse is None:
            return {}
        raw = getattr(providerResponse, "rawResponse", None)
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(providerResponse, dict):
            return dict(providerResponse)
        return {}

    @staticmethod
    def _buildNotifications(values) -> list[ResponseNotification]:
        items = []
        for value in list(values or []):
            if isinstance(value, ResponseNotification):
                items.append(value)
                continue
            payload = dict(value or {})
            items.append(
                ResponseNotification(
                    notificationId=str(payload.get("notificationId") or payload.get("id") or ""),
                    title=str(payload.get("title") or ""),
                    message=str(payload.get("message") or payload.get("content") or ""),
                    priority=str(payload.get("priority") or NotificationPriority.NORMAL.value),
                    category=str(payload.get("category") or "SYSTEM"),
                    deliveryMode=str(payload.get("deliveryMode") or "UI_ONLY"),
                    persistent=bool(payload.get("persistent", False)),
                    requiresAcknowledgement=bool(payload.get("requiresAcknowledgement", False)),
                    interruptAllowed=bool(payload.get("interruptAllowed", False)),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return items

    @staticmethod
    def _buildActions(values) -> list[ResponseAction]:
        items = []
        for value in list(values or []):
            if isinstance(value, ResponseAction):
                items.append(value)
                continue
            payload = dict(value or {})
            items.append(
                ResponseAction(
                    actionName=str(payload.get("actionName") or payload.get("name") or ""),
                    target=str(payload.get("target") or payload.get("toolName") or ""),
                    arguments=dict(payload.get("arguments") or {}),
                    description=str(payload.get("description") or ""),
                    source=str(payload.get("source") or ""),
                    requiresExecution=bool(payload.get("requiresExecution", True)),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return items

    def _buildFollowups(self, values) -> list[ResponseFollowup]:
        if not self._configEnabled("responses.responseFollowupsEnabled", True):
            return []
        items = []
        for value in list(values or []):
            if isinstance(value, ResponseFollowup):
                items.append(value)
                continue
            payload = dict(value or {})
            items.append(
                ResponseFollowup(
                    prompt=str(payload.get("prompt") or payload.get("question") or ""),
                    kind=str(payload.get("kind") or "clarification"),
                    required=bool(payload.get("required", False)),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return items

    def _buildMetadata(self, providerResponse, structured: dict[str, Any], metadata: dict | None = None) -> ResponseMetadata:
        if not self._configEnabled("responses.responseMetadataEnabled", True):
            return ResponseMetadata()
        providerName = str(getattr(providerResponse, "provider", "") or structured.get("provider") or "")
        nestedMetadata = structured.get("metadata") if isinstance(structured.get("metadata"), dict) else {}
        confidence = structured.get(
            "confidence",
            (metadata or {}).get("confidence") if metadata else None,
        )
        if confidence is None:
            confidence = nestedMetadata.get("confidence")
        if confidence is None:
            confidence = getattr(providerResponse, "confidence", 0.0) if providerResponse is not None else 0.0
        modules = list((metadata or {}).get("modulesInvolved") or structured.get("modulesInvolved") or nestedMetadata.get("modulesInvolved") or [])
        intents = list((metadata or {}).get("intentsResolved") or structured.get("intentsResolved") or nestedMetadata.get("intentsResolved") or [])
        memoryReferences = list((metadata or {}).get("memoryReferences") or structured.get("memoryReferences") or nestedMetadata.get("memoryReferences") or [])
        interruptionFlags = dict((metadata or {}).get("interruptionFlags") or structured.get("interruptionFlags") or nestedMetadata.get("interruptionFlags") or {})
        streamingEnabled = bool((metadata or {}).get("streamingEnabled", structured.get("streamingEnabled", nestedMetadata.get("streamingEnabled", False))))
        deliveryResults = dict((metadata or {}).get("deliveryResults") or structured.get("deliveryResults") or nestedMetadata.get("deliveryResults") or {})
        generationTime = getattr(providerResponse, "latency", None)
        if generationTime is None:
            generationTime = time()
        return ResponseMetadata(
            provider=providerName,
            generationTime=generationTime,
            confidence=float(confidence or 0.0),
            modulesInvolved=modules,
            intentsResolved=intents,
            memoryReferences=memoryReferences,
            interruptionFlags=interruptionFlags,
            streamingEnabled=streamingEnabled,
            deliveryResults=deliveryResults,
        )

    def _configEnabled(self, key: str, default: bool = True) -> bool:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
