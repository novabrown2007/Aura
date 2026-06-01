"""Ambiguity detection for Aura intents."""

from __future__ import annotations

from assistant.clarification.models import AmbiguityResult, ClarificationOption, ClarificationType
from assistant.clarification.strategies import IntentClarificationStrategy, ModuleClarificationStrategy, ParameterClarificationStrategy


class AmbiguityDetector:
    """Detect when an intent needs clarification."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Ambiguity") if logger else None

    def detect(self, sourceIntent: dict | None, executionContext: dict | None = None, candidates: list | None = None) -> AmbiguityResult:
        sourceIntent = dict(sourceIntent or {})
        arguments = dict(sourceIntent.get("arguments") or {})
        metadata = dict(sourceIntent.get("metadata") or {})
        required = list(metadata.get("requiredParameters") or sourceIntent.get("requiredParameters") or [])
        confidence = float(sourceIntent.get("confidence") or 0.0)

        if candidates and len(candidates) > 1:
            options = self._buildOptions(candidates)
            return AmbiguityResult(
                ambiguous=True,
                clarificationType=ClarificationType.MULTIPLE_OPTIONS,
                reason="Multiple valid targets exist.",
                question=ModuleClarificationStrategy.buildQuestion(sourceIntent, options),
                options=options,
                confidence=confidence,
                metadata={"candidates": [self._candidateValue(candidate) for candidate in candidates]},
            )

        missing = [parameter for parameter in required if parameter not in arguments or arguments.get(parameter) in (None, "", [])]
        if missing:
            parameter = missing[0]
            clarificationType = ParameterClarificationStrategy.parameterType(parameter)
            question = ParameterClarificationStrategy.buildQuestion(parameter, sourceIntent)
            return AmbiguityResult(
                ambiguous=True,
                clarificationType=clarificationType,
                reason=f"Missing required parameter: {parameter}",
                question=question,
                requiredParameter=parameter,
                confidence=confidence,
                metadata={"missingParameters": missing},
            )

        if confidence and confidence < float(self._config("llm.intent.confidenceThreshold", 0.75)):
            return AmbiguityResult(
                ambiguous=True,
                clarificationType=ClarificationType.LOW_CONFIDENCE,
                reason=f"Low confidence: {confidence}",
                question=IntentClarificationStrategy.buildQuestion(sourceIntent, ClarificationType.LOW_CONFIDENCE),
                confidence=confidence,
            )

        clarification = metadata.get("clarification")
        if isinstance(clarification, dict):
            options = self._buildOptions(clarification.get("options") or [])
            if clarification.get("required", True):
                return AmbiguityResult(
                    ambiguous=True,
                    clarificationType=ClarificationType(str(clarification.get("type") or "MISSING_PARAMETER")),
                    reason=str(clarification.get("reason") or "Clarification required."),
                    question=str(clarification.get("question") or ""),
                    options=options,
                    requiredParameter=str(clarification.get("requiredParameter") or ""),
                    confidence=confidence,
                    metadata=dict(clarification.get("metadata") or {}),
                )

        return AmbiguityResult(ambiguous=False, confidence=confidence)

    @staticmethod
    def _buildOptions(values) -> list[ClarificationOption]:
        options = []
        for value in list(values or []):
            if isinstance(value, ClarificationOption):
                options.append(value)
                continue
            payload = dict(value or {})
            options.append(
                ClarificationOption(
                    optionId=str(payload.get("optionId") or payload.get("id") or ""),
                    label=str(payload.get("label") or payload.get("title") or payload.get("value") or ""),
                    value=payload.get("value", payload.get("label")),
                    description=str(payload.get("description") or ""),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return options

    @staticmethod
    def _candidateValue(candidate):
        if isinstance(candidate, dict):
            return candidate.get("value") or candidate.get("label") or candidate.get("id")
        return getattr(candidate, "value", None) or getattr(candidate, "label", None) or getattr(candidate, "id", None)

    def _config(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
