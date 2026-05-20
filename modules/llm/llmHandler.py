"""
Compatibility LLM module for Aura.

The old LLMHandler talked directly to Ollama. It now owns Aura-specific
conversation concerns, then delegates all provider access to modules.llm.LLMManager.
"""

from __future__ import annotations

from typing import Any

from modules.llm.manager.llmManager import LLMManager
from modules.llm.intent.intentPipeline import IntentPipeline
from modules.llm.utils.responseValidator import ResponseValidator
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.base import AuraModule, ModuleMetadata


class LLMHandler(AuraModule):
    """Aura-facing LLM module that keeps existing callers stable."""

    metadata = ModuleMetadata(
        name="llm",
        version="1.1.0",
        description="Provider-neutral LLM prompt handling and response generation.",
        permissions=("network:http", "database:read", "database:write"),
        capabilities=("conversation", "memory", "llm"),
    )

    def __init__(self, context=None):
        """Initialize handler state and optionally bind to a runtime context."""

        super().__init__()
        self.logger = None
        self.historyEnabled = True
        self.historyLimit = 25
        self.memoryEnabled = True
        self.history = None
        self.memory = None
        self.manager = None
        self.intentPipeline = None

        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Initialize prompt-related settings and provider manager access."""

        super().initialize(context)
        self.context = context
        self.logger = context.logger.getChild("LLM") if context.logger else None

        config = context.config
        self.historyEnabled = config.get("llm.history.enabled", True)
        self.historyLimit = config.get("llm.history.limit", 25)
        self.memoryEnabled = config.get("llm.memory.enabled", True)

        self.history = context.conversationHistory
        self.memory = context.memoryManager
        self.manager = getattr(context, "llmManager", None)
        if self.manager is None:
            self.manager = LLMManager(context)
            context.llmManager = self.manager
        self.intentPipeline = IntentPipeline(context, self.manager)

        if self.logger:
            self.logger.info("Initialized provider-neutral LLM handler.")

    def getIntents(self):
        """Return intents handled directly by the LLM module."""

        return []

    def generateResponse(self, userInput: str) -> str:
        """Generate a conversational response while preserving legacy API shape."""

        systemPrompt = self._buildSystemPrompt()
        conversationHistory = self._getConversationHistory()
        if self._supportsIntentPipeline():
            cleaned = self.intentPipeline.handleUserInput(userInput, systemPrompt, conversationHistory)
            self._logConversation(userInput, cleaned)
            return cleaned

        response = self.manager.generateResponse(systemPrompt, userInput, conversationHistory)

        if not response.success:
            if self.logger:
                self.logger.error(f"LLM response failed: {response.error}")
            return "I am currently unable to access my language model."

        cleaned = response.text.strip() or "I don't have a response for that."
        toolResult = self._handleToolResponse(cleaned)
        if toolResult is not None:
            cleaned = toolResult

        self._logConversation(userInput, cleaned)
        return cleaned

    def _supportsIntentPipeline(self) -> bool:
        """Return whether the current manager can provide structured intent parsing."""

        return (
            self.intentPipeline is not None
            and hasattr(self.manager, "generateStructuredResponse")
            and not self._isOfflineMode()
        )

    def generateStructuredResponse(self, userInput: str, schema: dict) -> dict | None:
        """Generate structured JSON through the active provider."""

        response = self.manager.generateStructuredResponse(
            self._buildSystemPrompt(),
            userInput,
            schema,
            self._getConversationHistory(),
        )
        if not response.success:
            if self.logger:
                self.logger.error(f"Structured LLM response failed: {response.error}")
            return None
        return response.rawResponse if isinstance(response.rawResponse, dict) else None

    def _buildSystemPrompt(self) -> str:
        """Build Aura's base system prompt with optional memory injection."""

        memoryData = {}
        if self.memoryEnabled and self.memory:
            memoryData = self.memory.getMemory() or {}

        if self._isOfflineMode():
            return self._buildOfflineSystemPrompt(memoryData)

        basePrompt = """
You are Aura, a private AI assistant for Nova.

Purpose:
- Help with conversation, planning, reminders, calendar management, home automation, and general assistant tasks.
- Use long-term memory only as context; do not expose it unless it is relevant to the user's request.
- Use short-term conversation history to preserve continuity and resolve references like "that", "tomorrow", or "the event".
- Reason with the LLM, but execute real actions only through deterministic Aura tools.

Rules:
- Respond as Aura only.
- Do not speak for the user.
- Keep responses concise and helpful.
- Do not claim to access internal system data unless explicitly provided.
- If an action requires a tool, return the configured JSON tool-call format instead of pretending the action is complete.
- If required tool arguments are missing, ask a concise follow-up question instead of calling a tool.
"""
        return PromptBuilder.buildSystemPrompt(
            basePrompt,
            memory=memoryData,
            toolDefinitions=self._getToolSchemas(),
            profile="toolSelection",
        )

    def _buildOfflineSystemPrompt(self, memoryData: dict[str, Any]) -> str:
        """Build the offline prompt used when provider tooling is unavailable."""

        basePrompt = """
You are Aura, a private AI assistant for Nova running in offline mode.

Purpose:
- Help with normal conversation, planning, explanations, and lightweight reasoning.
- Use long-term memory only as context; do not expose it unless it is relevant to the user's request.
- Use short-term conversation history to preserve continuity and resolve references like "that", "tomorrow", or "the event".
- Offline mode cannot execute deterministic Aura tools or change external state.

Rules:
- Respond as Aura only.
- Do not speak for the user.
- Keep responses concise and helpful.
- Do not claim that you created, updated, deleted, started, stopped, or controlled anything.
- If the user asks for an action that would require a tool, respond with a generic message that the action cannot be completed in offline mode.
- Do not return JSON tool calls in offline mode.
"""
        return PromptBuilder.buildSystemPrompt(basePrompt, memory=memoryData)

    def _isOfflineMode(self) -> bool:
        """Return whether the active LLM manager is configured for offline mode."""

        return bool(getattr(self.manager, "offlineMode", False))

    def _getConversationHistory(self) -> list:
        """Return recent history when enabled."""

        if not self.historyEnabled or not self.history:
            return []
        return self.history.getRecentMessages(limit=self.historyLimit)

    def _logConversation(self, userInput: str, responseText: str):
        """Persist conversation messages without failing the response path."""

        if not self.history:
            return

        try:
            self.history.logMessage("user", userInput)
            self.history.logMessage("aura", responseText)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Conversation logging failed: {error}")

    def _getToolSchemas(self) -> list[dict[str, Any]]:
        """Return schemas exported by the central tool registry."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None:
            return []
        return registry.exportSchemas(offlineMode=self._isOfflineMode())

    def _handleToolResponse(self, text: str) -> str | None:
        """Execute tool calls returned by the LLM JSON contract."""

        parsed = self._parseToolResponse(text)
        if parsed is None:
            return None

        responseText = str(parsed.get("response") or "").strip()
        toolCalls = parsed.get("toolCalls") or parsed.get("tool_calls") or []
        if not isinstance(toolCalls, list) or not toolCalls:
            return responseText or None

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            return "I couldn't complete that because the tool executor is unavailable."

        results = executor.executeToolCalls(toolCalls, offlineMode=self._isOfflineMode())

        successful = [result for result in results if result.get("success")]
        failed = [result for result in results if not result.get("success")]
        if failed and not successful:
            return f"I couldn't complete that: {failed[0].get('error')}"
        if responseText:
            return responseText
        if successful:
            return "Done."
        return None

    @staticmethod
    def _parseToolResponse(text: str) -> dict[str, Any] | None:
        """Parse the JSON tool-call envelope if the model returned one."""

        valid, parsed, _ = ResponseValidator.parseJson(text)
        if not valid or not isinstance(parsed, dict):
            return None
        if "toolCalls" not in parsed and "tool_calls" not in parsed:
            return None
        return parsed
