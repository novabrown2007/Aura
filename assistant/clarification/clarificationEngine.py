"""Create clarification requests and responses."""

from __future__ import annotations

from time import time
from typing import Any

from assistant.clarification.ambiguityDetector import AmbiguityDetector
from assistant.clarification.models import AmbiguityResult, ClarificationOption, ClarificationRequest, ClarificationType
from assistant.clarification.strategies import IntentClarificationStrategy, ModuleClarificationStrategy, ParameterClarificationStrategy


class ClarificationEngine:
    """Generate natural clarification requests from ambiguity signals."""

    def __init__(self, context=None):
        self.context = context
        self.detector = AmbiguityDetector(context)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Engine") if logger else None

    def detect(self, sourceIntent: dict | None, executionContext: dict | None = None, candidates: list | None = None) -> AmbiguityResult:
        return self.detector.detect(sourceIntent, executionContext=executionContext, candidates=candidates)

    def createRequest(
        self,
        sourceIntent: dict | None,
        ambiguity: AmbiguityResult | None = None,
        conversationId: str = "default",
        requiredParameter: str = "",
        question: str = "",
        options: list[ClarificationOption] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ClarificationRequest:
        sourceIntent = dict(sourceIntent or {})
        ambiguity = ambiguity or self.detect(sourceIntent)
        options = list(options or ambiguity.options or [])
        if not question:
            question = ambiguity.question or self._question(sourceIntent, ambiguity, requiredParameter, options)
        timeoutSeconds = int(self._config("clarification.clarificationTimeoutSeconds", 60))
        now = time()
        return ClarificationRequest(
            conversationId=str(conversationId or "default"),
            sourceIntent=sourceIntent,
            clarificationType=ambiguity.clarificationType if ambiguity.ambiguous else ClarificationType.MISSING_PARAMETER,
            question=question,
            options=options,
            requiredParameter=requiredParameter or ambiguity.requiredParameter,
            createdAt=now,
            timeoutAt=now + timeoutSeconds,
            metadata=dict(metadata or ambiguity.metadata or {}),
        )

    def buildResponsePayload(self, request: ClarificationRequest) -> dict[str, Any]:
        return {
            "spokenText": request.question,
            "uiText": request.question,
            "followup": {
                "prompt": request.question,
                "kind": "clarification",
                "required": True,
                "metadata": {
                    "requestId": request.requestId,
                    "conversationId": request.conversationId,
                    "clarificationType": request.clarificationType.value if hasattr(request.clarificationType, "value") else str(request.clarificationType),
                    "requiredParameter": request.requiredParameter,
                    "options": [option.asDict() for option in request.options],
                    "metadata": dict(request.metadata or {}),
                },
            },
            "metadata": {
                "clarification": request.asDict(),
            },
        }

    def _question(self, sourceIntent: dict, ambiguity: AmbiguityResult, requiredParameter: str, options: list[ClarificationOption]) -> str:
        if ambiguity.clarificationType in {ClarificationType.MULTIPLE_OPTIONS, ClarificationType.TARGET_SELECTION}:
            return ModuleClarificationStrategy.buildQuestion(sourceIntent, options)
        if ambiguity.clarificationType in {ClarificationType.TIME_SELECTION, ClarificationType.LOCATION_SELECTION, ClarificationType.ACCOUNT_SELECTION}:
            return ParameterClarificationStrategy.buildQuestion(requiredParameter or ambiguity.requiredParameter, sourceIntent)
        if requiredParameter or ambiguity.requiredParameter:
            return ParameterClarificationStrategy.buildQuestion(requiredParameter or ambiguity.requiredParameter, sourceIntent)
        return IntentClarificationStrategy.buildQuestion(sourceIntent, ambiguity.clarificationType)

    def _config(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
