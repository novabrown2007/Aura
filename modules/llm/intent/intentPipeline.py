"""End-to-end structured intent pipeline for Aura."""

from __future__ import annotations

from typing import Any

from modules.llm.models.structuredIntent import StructuredIntent
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.llm.utils.responseValidator import ResponseValidator


class IntentPipeline:
    """Parse, validate, execute, and answer user requests through Aura tools."""

    INTENT_SCHEMA = {
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

    CONVERSATION_INTENTS = {"", "none", "conversation", "conversation.respond"}

    def __init__(self, context, manager):
        """Bind the pipeline to runtime services."""

        self.context = context
        self.manager = manager
        self.logger = context.logger.getChild("LLM.Intent") if getattr(context, "logger", None) else None
        self.threshold = self._getConfigValue("llm.intent.confidenceThreshold", 0.75)
        self.rawLogger = getattr(manager, "rawLogger", None)
        self.recentToolContext: list[dict[str, Any]] = []
        self.contextWindow = int(self._getConfigValue("llm.intent.contextWindow", 6))

    def handleUserInput(
        self,
        userInput: str,
        baseSystemPrompt: str,
        conversationHistory: list | None = None,
        confirmed: bool = False,
    ) -> str:
        """Run the complete cognition path from user input to final reply."""

        self._logStage("LLM", "Prompt Sent")
        intentResult = self.parseIntents(userInput, baseSystemPrompt, conversationHistory)
        if not intentResult["success"]:
            self._logStage("VALIDATION", intentResult["error"])
            return self._generateConversationReply(baseSystemPrompt, userInput, conversationHistory)

        intents = intentResult["intents"]
        self._logStage("INTENT", " -> ".join(intent.intent for intent in intents))

        lowConfidence = [intent for intent in intents if intent.confidence < self.threshold]
        if lowConfidence:
            lowest = min(lowConfidence, key=lambda item: item.confidence)
            self._logStage("VALIDATION", f"Confidence below threshold: {lowest.confidence}")
            return self.askClarification(lowest)

        if all(intent.intent in self.CONVERSATION_INTENTS for intent in intents):
            self._logStage("VALIDATION", "Conversation intent")
            return self._generateConversationReply(baseSystemPrompt, userInput, conversationHistory)

        validation = self.validateIntents(intents)
        if not validation["success"]:
            self._logStage("VALIDATION", validation["error"])
            return self.askClarification(intents[0], validation["error"])

        self._logStage("VALIDATION", "Success")
        executions = self.executeIntents(intents, confirmed=confirmed)
        failed = [execution for execution in executions if not execution.get("success")]
        self._logStage("EXECUTION", "Success" if not failed else failed[0].get("error", "Failed"))

        reply = self.generateExecutionReply(
            baseSystemPrompt,
            userInput,
            intents,
            executions,
            conversationHistory,
        )
        self._logStage("RESPONSE", "Generated")
        return reply

    def parseIntent(
        self,
        userInput: str,
        baseSystemPrompt: str,
        conversationHistory: list | None = None,
    ) -> dict[str, Any]:
        """Ask the structured provider to interpret user input as one intent."""

        result = self.parseIntents(userInput, baseSystemPrompt, conversationHistory)
        if not result.get("success"):
            return result
        return {"success": True, "intent": result["intents"][0]}

    def parseIntents(
        self,
        userInput: str,
        baseSystemPrompt: str,
        conversationHistory: list | None = None,
    ) -> dict[str, Any]:
        """Ask the structured provider to interpret user input as ordered intents."""

        registry = getattr(self.context, "toolRegistry", None)
        toolSchemas = registry.exportSchemas(offlineMode=self._isOfflineMode()) if registry else []
        contextualMemory = self.buildContextualMemory(userInput, conversationHistory)
        systemPrompt = PromptBuilder.buildIntentPrompt(
            baseSystemPrompt,
            toolSchemas,
            self.threshold,
            contextualMemory=contextualMemory,
        )
        response = self.manager.generateStructuredResponse(
            systemPrompt,
            userInput,
            self.INTENT_SCHEMA,
            conversationHistory,
        )
        if not response.success:
            return {"success": False, "error": response.error or "Intent parsing failed."}
        if not isinstance(response.rawResponse, dict):
            return {"success": False, "error": "Intent response was not a JSON object."}

        normalized = self._normalizeIntentPayload(response.rawResponse)
        valid, error = ResponseValidator.validateSchema(normalized, self.INTENT_SCHEMA)
        if not valid:
            return {"success": False, "error": error or "Intent schema validation failed."}
        intents = [StructuredIntent.fromDict(intent) for intent in normalized["intents"]]
        if not intents:
            return {"success": False, "error": "Intent response did not include any intents."}
        return {"success": True, "intents": intents, "response": normalized.get("response", "")}

    def buildContextualMemory(
        self,
        userInput: str,
        conversationHistory: list | None = None,
    ) -> dict[str, Any]:
        """Collect short-term, long-term, and runtime context for intent parsing."""

        return {
            "memory": self._getRelevantMemory(userInput),
            "recentConversation": self._formatRecentConversation(conversationHistory),
            "recentToolContext": self._formatRecentToolContext(),
            "runtimeState": self._getRuntimeState(),
        }

    def validateIntent(self, intent: StructuredIntent) -> dict[str, Any]:
        """Validate tool existence and arguments before execution."""

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            return {"success": False, "error": "Tool executor is unavailable."}

        valid, error = executor.validateToolCall(
            intent.intent,
            intent.arguments,
            offlineMode=self._isOfflineMode(),
        )
        return {"success": valid, "error": error}

    def validateIntents(self, intents: list[StructuredIntent]) -> dict[str, Any]:
        """Validate every non-conversation intent before executing the chain."""

        for intent in intents:
            if intent.intent in self.CONVERSATION_INTENTS:
                continue
            validation = self.validateIntent(intent)
            if not validation["success"]:
                return validation
        return {"success": True, "error": None}

    def executeIntent(self, intent: StructuredIntent, confirmed: bool = False) -> dict[str, Any]:
        """Execute a validated intent through the deterministic tool executor."""

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            return {"success": False, "toolName": intent.intent, "error": "Tool executor is unavailable."}
        return executor.executeToolCall(
            intent.intent,
            intent.arguments,
            offlineMode=self._isOfflineMode(),
            confirmed=confirmed,
        )

    def executeIntents(
        self,
        intents: list[StructuredIntent],
        confirmed: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute an ordered chain of validated intents."""

        executions = []
        for intent in intents:
            if intent.intent in self.CONVERSATION_INTENTS:
                continue
            execution = self.executeIntent(intent, confirmed=confirmed)
            executions.append(execution)
            self._rememberToolContext(intent, execution)
            if not execution.get("success"):
                break
        return executions

    def generateExecutionReply(
        self,
        baseSystemPrompt: str,
        userInput: str,
        intents: list[StructuredIntent],
        executions: list[dict[str, Any]],
        conversationHistory: list | None = None,
    ) -> str:
        """Generate the final user-facing reply from deterministic execution results."""

        failed = [execution for execution in executions if not execution.get("success")]
        if failed:
            return f"I couldn't complete that: {failed[0].get('error')}"

        resultPrompt = (
            f"{baseSystemPrompt.strip()}\n\n"
            "Aura executed deterministic tools in order. Generate a concise user-facing reply.\n"
            "Do not claim extra actions. Do not expose raw internal data unless useful.\n"
            f"Intents: {[intent.asDict() for intent in intents]}\n"
            f"Execution results: {executions}"
        )
        response = self.manager.generateResponse(resultPrompt, userInput, conversationHistory)
        if response.success and response.text.strip():
            return response.text.strip()
        fallback = next((intent.response for intent in intents if intent.response), "")
        return fallback or "Done."

    def askClarification(self, intent: StructuredIntent, reason: str | None = None) -> str:
        """Return a concise clarification request when intent confidence is too low."""

        if reason:
            return f"I need one more detail before I can do that: {reason}"
        return "I want to make sure I understood correctly. What exactly should I do?"

    def _generateConversationReply(
        self,
        baseSystemPrompt: str,
        userInput: str,
        conversationHistory: list | None = None,
    ) -> str:
        """Fallback to normal conversation generation."""

        response = self.manager.generateResponse(baseSystemPrompt, userInput, conversationHistory)
        if response.success and response.text.strip():
            return response.text.strip()
        return "I am currently unable to access my language model."

    def _isOfflineMode(self) -> bool:
        """Return whether the manager is in offline mode."""

        return bool(getattr(self.manager, "offlineMode", False))

    def _getConfigValue(self, key: str, default):
        """Read a pipeline config value."""

        config = getattr(self.context, "config", None)
        if config is None:
            return default
        return config.get(key, default)

    def _getRelevantMemory(self, userInput: str) -> dict[str, Any]:
        """Return memory entries useful for resolving contextual references."""

        memoryManager = getattr(self.context, "memoryManager", None)
        if memoryManager is None:
            return {}

        if hasattr(memoryManager, "summarizeMemories"):
            relevant = memoryManager.summarizeMemories(userInput)
            if relevant:
                return relevant

        if not hasattr(memoryManager, "getMemory"):
            return {}

        memory = memoryManager.getMemory() or {}
        if not isinstance(memory, dict):
            return {}

        if self._looksContextual(userInput):
            return memory

        tokens = self._tokenize(userInput)
        relevant = {}
        for key, value in memory.items():
            keyText = str(key).lower()
            valueText = str(value).lower()
            if keyText in {"current_room", "current_location", "room", "location"}:
                relevant[key] = value
                continue
            if any(token in keyText or token in valueText for token in tokens):
                relevant[key] = value
        return relevant

    def _formatRecentConversation(self, conversationHistory: list | None) -> list[str]:
        """Format recent conversation turns for reference resolution."""

        if not conversationHistory:
            return []

        formatted = []
        for message in conversationHistory[-self.contextWindow:]:
            if isinstance(message, dict):
                role = str(message.get("role") or message.get("author") or "user")
                content = str(message.get("content") or "")
            else:
                role, content = message
                role = str(role)
                content = str(content)
            formatted.append(f"{role}: {content}")
        return formatted

    def _formatRecentToolContext(self) -> list[str]:
        """Format recent tool executions for pronoun and follow-up resolution."""

        formatted = []
        for item in self.recentToolContext[-self.contextWindow:]:
            formatted.append(
                f"{item.get('intent')} arguments={item.get('arguments')} "
                f"success={item.get('success')} result={item.get('result')}"
            )
        return formatted

    def _getRuntimeState(self) -> dict[str, Any]:
        """Collect lightweight runtime state relevant to intent parsing."""

        state = {}
        homeAutomation = getattr(self.context, "homeAutomation", None)
        if homeAutomation is not None and hasattr(homeAutomation, "getLights"):
            try:
                lights = []
                for light in homeAutomation.getLights():
                    lights.append(
                        {
                            "device_id": getattr(light, "device_id", ""),
                            "name": getattr(light, "name", ""),
                            "room": getattr(light, "metadata", {}).get("room", ""),
                            "is_on": getattr(light, "is_on", None),
                            "brightness": getattr(light, "brightness", None),
                        }
                    )
                if lights:
                    state["lights"] = lights
            except Exception as error:
                if self.logger:
                    self.logger.debug(f"Runtime light context unavailable: {error}")
        return state

    def _rememberToolContext(self, intent: StructuredIntent, execution: dict[str, Any]):
        """Preserve recent tool executions for follow-up commands."""

        self.recentToolContext.append(
            {
                "intent": intent.intent,
                "arguments": intent.arguments,
                "success": execution.get("success", False),
                "result": execution.get("result"),
            }
        )
        if len(self.recentToolContext) > self.contextWindow:
            self.recentToolContext = self.recentToolContext[-self.contextWindow:]

    @staticmethod
    def _looksContextual(userInput: str) -> bool:
        """Return whether the user input likely needs prior context."""

        tokens = IntentPipeline._tokenize(userInput)
        contextualWords = {"it", "them", "that", "those", "there", "too", "also", "again", "same"}
        return bool(tokens & contextualWords)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenize user text for lightweight relevance checks."""

        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text))
        return {token for token in cleaned.split() if token}

    @staticmethod
    def _normalizeIntentPayload(payload: dict[str, Any]) -> dict[str, Any]:
        """Accept both the new chain shape and the old single-intent shape."""

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

    def _logStage(self, stage: str, message: str):
        """Log a readable structured pipeline stage."""

        line = f"[{stage}] {message}"
        if self.logger:
            self.logger.info(line)
        if self.rawLogger and hasattr(self.rawLogger, "logPipelineStage"):
            self.rawLogger.logPipelineStage(stage, message)
