"""Core tool reasoning contract and execution orchestration."""

from __future__ import annotations

import json
from typing import Any


class ToolOrchestrator:
    """
    Owns the runtime tool contract outside the LLM layer.

    Modules define tools, ModuleLoader registers them in ToolRegistry, and this
    service exposes schemas plus deterministic validation/execution helpers.
    LLMs only reason over the schemas and return candidate tool calls.
    """

    TOOL_INTENT_SCHEMA = {
        "type": "object",
        "required": ["intents"],
        "properties": {
            "response": {"type": "string"},
            "intents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["intent", "arguments", "confidence"],
                    "properties": {
                        "intent": {"type": "string"},
                        "arguments": {"type": "object"},
                        "confidence": {"type": "number"},
                        "response": {"type": "string"},
                    },
                },
            },
        },
    }
    TOOL_CALL_ENVELOPE_SCHEMA = {
        "type": "object",
        "required": ["response", "toolCalls"],
        "properties": {
            "response": {"type": "string"},
            "toolCalls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["toolName", "arguments"],
                    "properties": {
                        "toolName": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                },
            },
        },
    }
    CONVERSATION_INTENTS = {"", "none", "conversation", "conversation.respond"}

    def __init__(self, context):
        """Bind the orchestrator to runtime tool services."""

        self.context = context

    def exportSchemas(self, offlineMode: bool = False, **filters):
        """Return schemas for currently registered module-owned tools."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None:
            return []
        return registry.exportSchemas(offlineMode=offlineMode, **filters)

    def validateIntent(self, intent, offlineMode: bool = False):
        """Validate one candidate tool intent without executing it."""

        if self.isConversationIntent(getattr(intent, "intent", intent)):
            return {"success": True, "error": None}

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            return {"success": False, "error": "Tool executor is unavailable."}

        valid, error = executor.validateToolCall(
            intent.intent,
            intent.arguments,
            offlineMode=offlineMode,
        )
        return {"success": valid, "error": error}

    def validateIntents(self, intents: list, offlineMode: bool = False):
        """Validate a candidate tool chain."""

        for intent in intents:
            validation = self.validateIntent(intent, offlineMode=offlineMode)
            if not validation["success"]:
                return validation
        return {"success": True, "error": None}

    def executeIntent(self, intent, offlineMode: bool = False, confirmed: bool = False):
        """Execute one validated tool intent through ToolExecutor."""

        if self.isConversationIntent(intent.intent):
            return {"success": True, "toolName": intent.intent, "result": None}

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            return {"success": False, "toolName": intent.intent, "error": "Tool executor is unavailable."}

        return executor.executeToolCall(
            intent.intent,
            intent.arguments,
            offlineMode=offlineMode,
            confirmed=confirmed,
        )

    def executeIntents(self, intents: list, offlineMode: bool = False, confirmed: bool = False):
        """Execute an ordered tool chain until one step fails."""

        executions = []
        for intent in intents:
            if self.isConversationIntent(intent.intent):
                continue
            execution = self.executeIntent(intent, offlineMode=offlineMode, confirmed=confirmed)
            executions.append(execution)
            if not execution.get("success"):
                break
        return executions

    def executeToolEnvelope(self, text: str, offlineMode: bool = False):
        """Parse and execute the legacy JSON tool-call envelope."""

        parsed = self.parseToolEnvelope(text)
        if parsed is None:
            return None

        response_text = str(parsed.get("response") or "").strip()
        tool_calls = parsed.get("toolCalls") or parsed.get("tool_calls") or []
        if not isinstance(tool_calls, list) or not tool_calls:
            return response_text or None

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            return "I couldn't complete that because the tool executor is unavailable."

        results = executor.executeToolCalls(tool_calls, offlineMode=offlineMode)
        successful = [result for result in results if result.get("success")]
        failed = [result for result in results if not result.get("success")]
        if failed and not successful:
            return f"I couldn't complete that: {failed[0].get('error')}"
        if response_text:
            return response_text
        if successful:
            return "Done."
        return None

    @classmethod
    def normalizeIntentPayload(cls, payload: dict[str, Any]):
        """Accept both the chain shape and the old single-intent shape."""

        if isinstance(payload.get("intents"), list):
            return payload
        if "intent" in payload:
            return {
                "response": payload.get("response", ""),
                "intents": [
                    {
                        "intent": payload.get("intent", ""),
                        "arguments": payload.get("arguments", {}),
                        "confidence": payload.get("confidence", 0.0),
                        "response": payload.get("response", ""),
                    }
                ],
            }
        return payload

    @classmethod
    def isConversationIntent(cls, intent_name: str):
        """Return whether an intent is conversational rather than executable."""

        return str(intent_name) in cls.CONVERSATION_INTENTS

    @staticmethod
    def parseToolEnvelope(text: str):
        """Parse a JSON envelope containing `toolCalls` if present."""

        try:
            parsed = json.loads(str(text))
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(parsed, dict):
            return None
        if "toolCalls" not in parsed and "tool_calls" not in parsed:
            return None
        return parsed
