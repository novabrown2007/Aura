"""Trust scoring for Aura execution governance."""

from __future__ import annotations


class TrustEvaluator:
    """Evaluate whether a request is trustworthy enough to execute."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Trust") if logger else None

    def evaluate(self, request, tool=None):
        score = 0.8
        requestedBy = str(getattr(request, "requestedBy", "") or "").lower()
        source = str(getattr(request, "source", "") or "").lower()
        metadata = getattr(request, "metadata", {}) or {}
        if hasattr(metadata, "asDict"):
            metadata = metadata.asDict()
        confidence = float((metadata or {}).get("confidence", 0.0) or 0.0)

        if requestedBy in {"automation", "system"} or source in {"automation", "automation_composer"}:
            score = min(score, 0.45)
        if requestedBy in {"llm", "provider"}:
            score = min(score, 0.65)
        if confidence:
            score = min(1.0, (score + confidence) / 2.0)
        return score
