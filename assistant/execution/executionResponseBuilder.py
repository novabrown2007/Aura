"""Build assistant-facing responses from execution results."""

from __future__ import annotations

from assistant.responses.models import AssistantResponse, ResponseAction, ResponseNotification, ResponseFollowup, ResponseMetadata


class ExecutionResponseBuilder:
    """Convert execution responses into structured assistant responses."""

    def __init__(self, context=None):
        self.context = context

    def build(self, request, response, actionDefinition=None):
        result = response.result if hasattr(response, "result") else response
        actionName = str(getattr(actionDefinition, "actionName", "") or getattr(request, "action", "") or "")
        spokenText, uiText = self._format(actionName, result, response)
        metadata = ResponseMetadata(
            provider="execution",
            generationTime=float(getattr(response, "executionTime", 0.0) or 0.0),
            confidence=1.0 if getattr(response, "status", "") == "COMPLETED" else 0.5,
            modulesInvolved=[str(getattr(actionDefinition, "module", "") or "")] if getattr(actionDefinition, "module", "") else [],
            intentsResolved=[str(getattr(request, "intent", "") or actionName)] if actionName else [],
            memoryReferences=[],
            interruptionFlags={"execution": True},
            streamingEnabled=False,
            deliveryResults={},
        )
        followups = []
        if getattr(response, "status", "") == "REQUIRES_CONFIRMATION":
            followups.append(ResponseFollowup(prompt=f"Please confirm {actionName}.").asDict())
        return AssistantResponse(
            spokenText=spokenText,
            uiText=uiText,
            notifications=self._notifications(response),
            actions=[ResponseAction(actionName=actionName, target=actionName, arguments=dict(getattr(request, "parameters", {}) or {}), source="execution")],
            metadata=metadata,
            followups=[ResponseFollowup(**item) if isinstance(item, dict) else item for item in followups],
            priority="NORMAL",
        )

    @staticmethod
    def _format(actionName: str, result, response):
        if getattr(response, "status", "") == "REQUIRES_CONFIRMATION":
            return f"Please confirm {actionName}.", f"Confirmation required for {actionName}."
        if getattr(response, "status", "") == "DENIED":
            return str(response.errors[0] if getattr(response, "errors", []) else "Action denied."), str(response.errors[0] if getattr(response, "errors", []) else "Action denied.")
        if isinstance(result, dict):
            text = result.get("spokenText") or result.get("message") or result.get("result") or f"Completed {actionName}."
            ui = result.get("uiText") or text
            return str(text), str(ui)
        if result is None:
            return f"Completed {actionName}.", f"Completed {actionName}."
        return f"Completed {actionName}.", str(result)

    @staticmethod
    def _notifications(response):
        if getattr(response, "status", "") != "COMPLETED":
            return []
        warnings = list(getattr(response, "warnings", []) or [])
        if not warnings:
            return []
        return [ResponseNotification(title="Execution warning", message=warning, priority="NORMAL", category="SYSTEM") for warning in warnings]
