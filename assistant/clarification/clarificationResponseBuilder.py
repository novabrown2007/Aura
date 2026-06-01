"""Build structured assistant responses for clarification prompts."""

from __future__ import annotations

from assistant.responses import AssistantResponse, ResponseContext, ResponseFollowup, ResponseMetadata


class ClarificationResponseBuilder:
    """Create structured clarification response packets."""

    def __init__(self, context=None, contextManager=None):
        self.context = context
        self.contextManager = contextManager
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Response") if logger else None

    def buildRequestResponse(self, request, conversationContext: dict | None = None) -> AssistantResponse:
        payload = request.asDict() if hasattr(request, "asDict") else dict(request or {})
        followupMetadata = {
            "requestId": payload.get("requestId", ""),
            "conversationId": payload.get("conversationId", ""),
            "clarificationType": payload.get("clarificationType", ""),
            "requiredParameter": payload.get("requiredParameter", ""),
            "options": list(payload.get("options") or []),
            "metadata": dict(payload.get("metadata") or {}),
        }
        context = self._buildContext(conversationContext, payload)
        return AssistantResponse(
            spokenText=str(payload.get("question") or ""),
            uiText=str(payload.get("question") or ""),
            followups=[
                ResponseFollowup(
                    prompt=str(payload.get("question") or ""),
                    kind="clarification",
                    required=True,
                    metadata=followupMetadata,
                    options=list(payload.get("options") or []),
                )
            ],
            metadata=ResponseMetadata(notes={"clarification": payload}),
            context=context,
            requiresAcknowledgement=True,
            priority="HIGH",
        )

    def buildResolvedResponse(self, request, resolution: dict | None = None) -> AssistantResponse:
        payload = request.asDict() if hasattr(request, "asDict") else dict(request or {})
        resolution = dict(resolution or {})
        spokenText = str(resolution.get("spokenText") or payload.get("question") or "")
        uiText = str(resolution.get("uiText") or spokenText)
        metadata = ResponseMetadata(notes={"clarification": payload, "resolution": resolution})
        return AssistantResponse(
            spokenText=spokenText,
            uiText=uiText,
            metadata=metadata,
            context=self._buildContext(None, payload),
        )

    def _buildContext(self, conversationContext: dict | None, clarification: dict | None) -> ResponseContext:
        if self.contextManager is not None and hasattr(self.contextManager, "buildContext"):
            responseContext = self.contextManager.buildContext("")
            try:
                responseContext.clarification = dict(clarification or {})
            except Exception:
                pass
            return responseContext
        return ResponseContext(conversation=dict(conversationContext or {}), clarification=dict(clarification or {}))
