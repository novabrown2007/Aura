"""Raw LLM request/response logging for debugging cognition flows."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class LLMLogger:
    """Write raw LLM exchange logs when enabled by configuration."""

    def __init__(self, context=None):
        """Configure logging from runtime config."""

        self.context = context
        config = context.config if context else None
        self.enabled = bool(config.get("llm.logging.enabled", True)) if config else True
        self.path = Path(config.get("llm.logging.path", "logs/llm")) if config else Path("logs/llm")

    def logExchange(
        self,
        provider: str,
        methodName: str,
        systemPrompt: str,
        userPrompt: str,
        response,
        schema: dict[str, Any] | None = None,
        conversationHistory: list | None = None,
    ):
        """Persist one raw LLM exchange."""

        if not self.enabled:
            return

        self.path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        logPath = self.path / f"{timestamp}_{provider}_{methodName}.json"
        payload = {
            "timestamp": timestamp,
            "provider": provider,
            "method": methodName,
            "systemPrompt": systemPrompt,
            "userPrompt": userPrompt,
            "conversationHistory": conversationHistory or [],
            "schema": schema,
            "success": getattr(response, "success", False),
            "text": getattr(response, "text", ""),
            "error": getattr(response, "error", None),
            "latency": getattr(response, "latency", None),
            "tokenUsage": getattr(response, "tokenUsage", None),
            "finishReason": getattr(response, "finishReason", None),
        }
        logPath.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def logPipelineStage(self, stage: str, message: str):
        """Append one structured cognition pipeline stage to a daily log."""

        if not self.enabled:
            return

        self.path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat()
        logPath = self.path / "intent_pipeline.log"
        with logPath.open("a", encoding="utf-8") as logFile:
            logFile.write(f"{timestamp} [{stage}] {message}\n")
