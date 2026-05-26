"""
Compatibility LLM module for Aura.

The old LLMHandler talked directly to Ollama. It now owns Aura-specific
conversation concerns, then delegates all provider access to modules.llm.LLMManager.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime
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
        profileReply = self._tryAnswerProfileQuestion(userInput)
        if profileReply is not None:
            cleaned = self._cleanResponseText(profileReply)
            self._logConversation(userInput, cleaned)
            self._emit("response.generated", {"text": cleaned})
            self._speakResponse(cleaned)
            return cleaned

        if self._isOfflineMode() and not self._canAttemptStructuredOutput() and self._looksLikeToolRequest(userInput):
            cleaned = self._offlineToolUnavailableMessage()
            self._logConversation(userInput, cleaned)
            self._emit("response.generated", {"text": cleaned})
            self._speakResponse(cleaned)
            return cleaned

        systemPrompt = self._buildSystemPrompt(userInput)
        conversationHistory = self._getConversationHistory()
        if self._shouldUseIntentPipeline(userInput):
            cleaned = self._cleanResponseText(self.intentPipeline.handleUserInput(userInput, systemPrompt, conversationHistory))
            self._logConversation(userInput, cleaned)
            self._emit("response.generated", {"text": cleaned})
            self._speakResponse(cleaned)
            return cleaned

        response = self.manager.generateResponse(systemPrompt, userInput, conversationHistory)

        if not response.success:
            if self.logger:
                self.logger.error(f"LLM response failed: {response.error}")
            return self._providerFailureMessage(response.error)

        cleaned = self._cleanResponseText(response.text) or "I don't have a response for that."
        toolResult = self._handleToolResponse(cleaned)
        if toolResult is not None:
            cleaned = self._cleanResponseText(toolResult)

        self._logConversation(userInput, cleaned)
        self._emit("response.generated", {"text": cleaned})
        self._speakResponse(cleaned)
        return cleaned

    def _supportsIntentPipeline(self) -> bool:
        """Return whether the current manager can provide structured intent parsing."""

        return (
            self.intentPipeline is not None
            and hasattr(self.manager, "generateStructuredResponse")
            and (not self._isOfflineMode() or self._canAttemptStructuredOutput())
        )

    def _shouldUseIntentPipeline(self, userInput: str) -> bool:
        """Return whether the request likely needs structured tool parsing."""

        if not self._supportsIntentPipeline():
            return False
        if self.intentPipeline and getattr(self.intentPipeline, "pendingClarification", None):
            return True
        return self._looksLikeToolRequest(userInput)

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

        if self._effectiveOfflineMode():
            prompt = self._buildOfflineSystemPrompt({} if hasattr(self.memory, "injectPrompt") else memoryData)
            return self._injectMemoryPrompt(prompt, userInput, conversationHistory)

        basePrompt = """
You are Aura, a private AI assistant for Nova.

Current date: {currentDate}.

Purpose:
- Help with conversation, planning, reminders, calendar management, home automation, and general assistant tasks.
- Use long-term memory only as context; do not expose it unless it is relevant to the user's request.
- Use short-term conversation history to preserve continuity and resolve references like "that", "tomorrow", or "the event".
- Reason with the LLM, but execute real actions only through deterministic Aura tools.

Rules:
- Respond as Aura only.
- Do not prefix replies with "Aura:".
- Do not speak for the user.
- Keep responses concise and helpful.
- Do not claim to access internal system data unless explicitly provided.
- If an action requires a tool, return the configured JSON tool-call format instead of pretending the action is complete.
- If required tool arguments are missing, ask a concise follow-up question instead of calling a tool.
""".format(currentDate=date.today().isoformat())
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

Current date: {currentDate}.

Purpose:
- Help with normal conversation, planning, explanations, and lightweight reasoning.
- Use long-term memory only as context; do not expose it unless it is relevant to the user's request.
- Use short-term conversation history to preserve continuity and resolve references like "that", "tomorrow", or "the event".
- Offline mode cannot execute deterministic Aura tools or change external state.

Rules:
- Respond as Aura only.
- Do not prefix replies with "Aura:".
- Do not speak for the user.
- Keep responses concise and helpful.
- Do not claim that you created, updated, deleted, started, stopped, or controlled anything.
- If the user asks for an action that would require a tool, respond with a generic message that the action cannot be completed in offline mode.
- Do not return JSON tool calls in offline mode.
""".format(currentDate=date.today().isoformat())
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

    def _effectiveOfflineMode(self) -> bool:
        """Return whether this request should use the offline conversation path."""

        return self._isOfflineMode() and not self._canAttemptStructuredOutput()

    def _canAttemptStructuredOutput(self) -> bool:
        """Return whether the manager can attempt Gemini/tool parsing now."""

        if hasattr(self.manager, "canUseStructuredOutput"):
            return bool(self.manager.canUseStructuredOutput())
        return not self._isOfflineMode()

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

        return self.tools.exportSchemas(offlineMode=self._effectiveOfflineMode())

    def _handleToolResponse(self, text: str) -> str | None:
        """Execute tool calls returned by the LLM JSON contract."""

        return self.tools.executeToolEnvelope(text, offlineMode=self._effectiveOfflineMode())

    def _offlineToolUnavailableMessage(self) -> str:
        """Explain that device/tool actions are temporarily unavailable."""

        status = self.manager.getStatus() if hasattr(self.manager, "getStatus") else {}
        reason = status.get("offlineReason") or "the structured tool provider is unavailable"
        return (
            "I can control devices through Aura's Gemini tool path, but that path is temporarily unavailable. "
            f"Current fallback is {status.get('activeModel', 'offline mode')}. "
            f"Reason: {reason}"
        )

    @staticmethod
    def _looksLikeToolRequest(userInput: str) -> bool:
        """Return whether a user message appears to require deterministic tools."""

        text = str(userInput or "").lower()
        actionWords = {
            "turn", "switch", "set", "dim", "brighten", "create", "add",
            "remind", "schedule", "start", "stop", "open", "close", "delete",
            "update", "change", "put", "do", "run",
        }
        deviceWords = {
            "light", "lights", "lamp", "lamps", "reminder", "calendar", "event",
            "task", "camera", "stream", "automation", "brightness", "color",
            "action", "actions",
        }
        temporalWords = {
            "today", "tomorrow", "tonight", "morning", "afternoon", "evening",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
            "sunday",
        }
        tokens = set(re.findall(r"[a-z0-9_]+", text))
        if not tokens & actionWords:
            return False
        if tokens & deviceWords:
            return True
        if tokens & {"add", "create", "schedule", "remind", "put"} and tokens & temporalWords:
            return True
        if re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm)?\b", text) and tokens & {"add", "create", "schedule", "put"}:
            return True
        return False

    def _tryAnswerProfileQuestion(self, userInput: str) -> str | None:
        """Answer simple personal profile questions deterministically from memory."""

        lowered = str(userInput or "").lower()
        asksAge = bool(re.search(r"\b(how old|age)\b", lowered))
        asksName = bool(re.search(r"\b(my name|what(?:'s| is) my name|tell me my name)\b", lowered))
        asksSexuality = bool(re.search(r"\b(sexuality|sexual orientation)\b", lowered))
        if not any((asksAge, asksName, asksSexuality)):
            return None

        memoryText = self._profileMemoryText()
        parts = []
        if asksName:
            parts.append("your name is Nova")
        if asksAge:
            age = self._ageFromMemory(memoryText)
            if age is None:
                return None
            parts.append(f"you are {age} years old")
        if asksSexuality:
            sexuality = self._sexualityFromMemory(memoryText)
            if sexuality:
                parts.append(f"your sexual orientation is {sexuality}")

        if not parts:
            return None
        if len(parts) == 1:
            return parts[0][0].upper() + parts[0][1:] + "."
        return "You asked for profile info: " + "; ".join(parts) + "."

    def _profileMemoryText(self) -> str:
        """Collect memory text for deterministic profile extraction."""

        memory = self.memory
        if memory is None:
            return ""
        texts: list[str] = []
        try:
            if hasattr(memory, "retrieveMemories"):
                for item in memory.retrieveMemories(limit=20):
                    texts.append(str(getattr(item, "content", "")))
            elif hasattr(memory, "getMemory"):
                data = memory.getMemory() or {}
                if isinstance(data, dict):
                    texts.extend(str(value) for value in data.values())
        except Exception as error:
            if self.logger:
                self.logger.debug(f"Profile memory extraction failed: {error}")
        return "\n".join(text for text in texts if text)

    def _ageFromMemory(self, memoryText: str) -> int | None:
        """Calculate age from a remembered birth date, falling back to stated age."""

        birthDate = self._birthDateFromText(memoryText)
        if birthDate is not None:
            today = date.today()
            return today.year - birthDate.year - ((today.month, today.day) < (birthDate.month, birthDate.day))

        match = re.search(r"\b(?:i am|i'm)\s+(\d{1,3})\s+years?\s+old\b", memoryText, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _birthDateFromText(text: str) -> date | None:
        """Parse common remembered birthday formats."""

        cleaned = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", str(text or ""), flags=re.IGNORECASE)
        monthNames = "|".join(calendar.month_name[1:])
        match = re.search(rf"\b({monthNames})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", cleaned, flags=re.IGNORECASE)
        if match:
            month = list(calendar.month_name).index(match.group(1).capitalize())
            return date(int(match.group(3)), month, int(match.group(2)))

        match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", cleaned)
        if match:
            first, second, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if first > 12:
                return date(year, second, first)
            return date(year, first, second)
        return None

    @staticmethod
    def _sexualityFromMemory(memoryText: str) -> str | None:
        """Extract sexual orientation without conflating gender identity."""

        lowered = str(memoryText or "").lower()
        orientations = [
            "omnisexual",
            "bisexual",
            "pansexual",
            "asexual",
            "lesbian",
            "gay",
            "straight",
            "heterosexual",
            "homosexual",
        ]
        for orientation in orientations:
            if re.search(rf"\b{re.escape(orientation)}\b", lowered):
                return orientation
        return None

    @staticmethod
    def _cleanResponseText(text: str) -> str:
        """Normalize provider text before sending it to interfaces."""

        cleaned = str(text or "").strip()
        cleaned = re.sub(r"^(?:Aura|Assistant)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned

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
