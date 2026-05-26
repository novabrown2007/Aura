"""
Compatibility LLM module for Aura.

The old LLMHandler talked directly to Ollama. It now owns Aura-specific
conversation concerns, then delegates all provider access to modules.llm.LLMManager.
"""

from __future__ import annotations

from typing import Any

from core.tools.toolOrchestrator import ToolOrchestrator
from modules.llm.manager.llmManager import LLMManager
from modules.llm.intent.intentPipeline import IntentPipeline
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.base import AuraModule, ModuleMetadata


class LLMHandler(AuraModule):
    """Aura-facing LLM module that keeps existing callers stable."""

    metadata = ModuleMetadata(
        name="llm",
        version="1.4.0",
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
        self.tools = None

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
        self.tools = getattr(context, "toolOrchestrator", None) or ToolOrchestrator(context)
        self.intentPipeline = IntentPipeline(context, self.manager)

        if self.logger:
            self.logger.info("Initialized provider-neutral LLM handler.")

    def getIntents(self):
        """Return intents handled directly by the LLM module."""

        return []

    def generateResponse(self, userInput: str) -> str:
        """Generate a conversational response while preserving legacy API shape."""

        self._emit("message.received", {"text": userInput})
        systemPrompt = self._buildSystemPrompt(userInput)
        conversationHistory = self._getConversationHistory()
        if self._supportsIntentPipeline():
            cleaned = self.intentPipeline.handleUserInput(userInput, systemPrompt, conversationHistory)
            self._logConversation(userInput, cleaned)
            self._emit("response.generated", {"text": cleaned})
            self._speakResponse(cleaned)
            return cleaned

        response = self.manager.generateResponse(systemPrompt, userInput, conversationHistory)

        if not response.success:
            if self.logger:
                self.logger.error(f"LLM response failed: {response.error}")
            return self._providerFailureMessage(response.error)

        cleaned = response.text.strip() or "I don't have a response for that."
        toolResult = self._handleToolResponse(cleaned)
        if toolResult is not None:
            cleaned = toolResult

        self._logConversation(userInput, cleaned)
        self._emit("response.generated", {"text": cleaned})
        self._speakResponse(cleaned)
        return cleaned

    def _supportsIntentPipeline(self) -> bool:
        """Return whether the current manager can provide structured intent parsing."""

        return (
            self.intentPipeline is not None
            and hasattr(self.manager, "generateStructuredResponse")
            and not self._isOfflineMode()
        )

    @staticmethod
    def _providerFailureMessage(error: str | None = None) -> str:
        """Return a clear user-facing message when no LLM provider can answer."""

        if error:
            return f"I can't reach an available language provider right now. Last provider error: {error}"
        return "I can't reach an available language provider right now."

    def generateStructuredResponse(self, userInput: str, schema: dict) -> dict | None:
        """Generate structured JSON through the active provider."""

        response = self.manager.generateStructuredResponse(
            self._buildSystemPrompt(userInput),
            userInput,
            schema,
            self._getConversationHistory(),
        )
        if not response.success:
            if self.logger:
                self.logger.error(f"Structured LLM response failed: {response.error}")
            return None
        return response.rawResponse if isinstance(response.rawResponse, dict) else None

    def _buildSystemPrompt(self, userInput: str = "") -> str:
        """Build Aura's base system prompt with optional memory injection."""

        memoryData = {}
        conversationHistory = self._getConversationHistory()
        if self.memoryEnabled and self.memory:
            if hasattr(self.memory, "injectPrompt"):
                memoryData = {}
            elif hasattr(self.memory, "getContext"):
                memoryData = self.memory.getContext(userInput, conversationHistory=conversationHistory) or {}
            else:
                memoryData = self.memory.getMemory() or {}

        if self._isOfflineMode():
            prompt = self._buildOfflineSystemPrompt({} if hasattr(self.memory, "injectPrompt") else memoryData)
            return self._injectMemoryPrompt(prompt, userInput, conversationHistory)

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
        prompt = PromptBuilder.buildSystemPrompt(
            basePrompt,
            memory={} if hasattr(self.memory, "injectPrompt") else memoryData,
            toolDefinitions=self._getToolSchemas(),
            profile="conversation",
        )
        return self._injectMemoryPrompt(prompt, userInput, conversationHistory)

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

    def _injectMemoryPrompt(self, prompt: str, userInput: str, conversationHistory: list | None = None) -> str:
        """Inject tuned memory context when the structured memory pipeline is available."""

        if not self.memoryEnabled or not self.memory or not hasattr(self.memory, "injectPrompt"):
            return prompt
        try:
            injected, _ = self.memory.injectPrompt(
                prompt,
                userInput,
                conversationHistory=conversationHistory or [],
            )
            return injected
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Memory prompt injection failed: {error}")
            return prompt

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

        return self.tools.exportSchemas(offlineMode=self._isOfflineMode())

    def _handleToolResponse(self, text: str) -> str | None:
        """Execute tool calls returned by the LLM JSON contract."""

        return self.tools.executeToolEnvelope(text, offlineMode=self._isOfflineMode())

    def _speakResponse(self, text: str):
        """Send assistant text through the shared voice output interface when available."""

        text = str(text or "").strip()
        if not text:
            return

        voice = getattr(self.context, "voiceManager", None)
        if voice is None or not getattr(voice, "outputEnabled", False):
            return

        try:
            voice.speakResponse(text)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice playback failed: {error}")

    def _emit(self, eventName: str, data: dict):
        """Emit conversation events without coupling LLM code to memory internals."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"LLM event emission failed: {error}")
