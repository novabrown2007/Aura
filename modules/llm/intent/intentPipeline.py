"""End-to-end structured intent pipeline for Aura."""

from __future__ import annotations

import re
from typing import Any

from core.tools.toolOrchestrator import ToolOrchestrator
from modules.llm.models.structuredIntent import StructuredIntent
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.llm.utils.responseValidator import ResponseValidator


class IntentPipeline:
    """Parse, validate, execute, and answer user requests through Aura tools."""

    def __init__(self, context, manager):
        """Bind the pipeline to runtime services."""

        self.context = context
        self.manager = manager
        self.tools = getattr(context, "toolOrchestrator", None) or ToolOrchestrator(context)
        self.logger = context.logger.getChild("LLM.Intent") if getattr(context, "logger", None) else None
        self.threshold = self._getConfigValue("llm.intent.confidenceThreshold", 0.75)
        self.rawLogger = getattr(manager, "rawLogger", None)
        self.recentToolContext: list[dict[str, Any]] = []
        self.contextWindow = int(self._getConfigValue("llm.intent.contextWindow", 6))
        self.pendingClarification: dict[str, Any] | None = None
        self.lastClarification: dict[str, Any] | None = None
        self.clarificationManager = self._clarificationManager()

    def handleUserInput(
        self,
        userInput: str,
        baseSystemPrompt: str,
        conversationHistory: list | None = None,
        confirmed: bool = False,
    ) -> str:
        """Run the complete cognition path from user input to final reply."""

        pendingReply = self._tryResolvePendingClarification(
            userInput,
            baseSystemPrompt,
            conversationHistory,
            confirmed=confirmed,
        )
        if pendingReply is not None:
            return pendingReply

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
            self._storePendingClarification(lowest, f"Low confidence: {lowest.confidence}")
            return self.askClarification(lowest)

        if all(self.tools.isConversationIntent(intent.intent) for intent in intents):
            self._logStage("VALIDATION", "Conversation intent")
            return self._generateConversationReply(baseSystemPrompt, userInput, conversationHistory)

        validation = self.validateIntents(intents)
        if not validation["success"]:
            repaired = self._repairMissingArgumentFromInput(intents, validation["error"], userInput)
            if repaired is not None:
                intents = repaired
                validation = self.validateIntents(intents)
                if validation["success"]:
                    self._logStage("VALIDATION", "Repaired missing argument from user input")
                else:
                    self._logStage("VALIDATION", validation["error"])
            if validation["success"]:
                return self._executeValidatedIntents(
                    baseSystemPrompt,
                    userInput,
                    intents,
                    conversationHistory,
                    confirmed=confirmed,
                )
            self._logStage("VALIDATION", validation["error"])
            self._storePendingClarification(intents[0], validation["error"])
            return self.askClarification(intents[0], validation["error"])

        return self._executeValidatedIntents(
            baseSystemPrompt,
            userInput,
            intents,
            conversationHistory,
            confirmed=confirmed,
        )

    def _executeValidatedIntents(
        self,
        baseSystemPrompt: str,
        userInput: str,
        intents: list[StructuredIntent],
        conversationHistory: list | None = None,
        confirmed: bool = False,
    ) -> str:
        """Execute already-validated intents and generate the final reply."""

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

    def _tryResolvePendingClarification(
        self,
        userInput: str,
        baseSystemPrompt: str,
        conversationHistory: list | None = None,
        confirmed: bool = False,
    ) -> str | None:
        """Use a short follow-up answer to complete a pending tool intent."""

        if self.pendingClarification is None:
            return None

        if self._isCancellation(userInput):
            self.pendingClarification = None
            self.lastClarification = None
            self._completeConversationClarification()
            self._logStage("CLARIFICATION", "Cancelled pending intent")
            return "Okay, I won't worry about that for now."

        missingParameter = self.pendingClarification.get("missingParameter")
        pendingIntent = self.pendingClarification.get("intent")
        sessionId = str(self.pendingClarification.get("sessionId") or "")

        if self.clarificationManager is not None and sessionId:
            try:
                resolution = self.clarificationManager.resolveResponse(
                    userInput,
                    conversationId=self._clarificationConversationId(),
                    sessionId=sessionId,
                )
            except Exception as error:
                resolution = {"resolved": False, "reason": str(error)}

            if resolution.get("resolved"):
                resolvedValue = resolution.get("result", {}).get("value")
                if resolvedValue is None and missingParameter:
                    resolvedValue = self._extractClarificationValue(userInput, missingParameter, allowBare=True)
                if missingParameter and isinstance(pendingIntent, StructuredIntent):
                    completedIntent = self._withUpdatedArgument(pendingIntent, missingParameter, resolvedValue)
                    validation = self.validateIntents([completedIntent])
                    if not validation["success"]:
                        self._storePendingClarification(completedIntent, validation["error"])
                        return self.askClarification(completedIntent, validation["error"])

                    self.pendingClarification = None
                    self.lastClarification = None
                    self._completeConversationClarification()
                    self._logStage("CLARIFICATION", f"Resolved {missingParameter}")
                    return self._executeValidatedIntents(
                        baseSystemPrompt,
                        userInput,
                        [completedIntent],
                        conversationHistory,
                        confirmed=confirmed,
                    )

                self.pendingClarification = None
                self.lastClarification = None
                self._completeConversationClarification()
                self._logStage("CLARIFICATION", "Resolved clarification")
                return None

            if resolution.get("cancelled") or resolution.get("timedOut"):
                self.pendingClarification = None
                self.lastClarification = None
                self._completeConversationClarification()
                self._logStage("CLARIFICATION", "Stale clarification cleared")
                return None

        if not missingParameter or not isinstance(pendingIntent, StructuredIntent):
            self.pendingClarification = None
            self.lastClarification = None
            self._completeConversationClarification()
            return None

        value = self._extractClarificationValue(userInput, missingParameter, allowBare=True)
        if value is None:
            if self._looksLikeNewConversation(userInput):
                self.pendingClarification = None
                self.lastClarification = None
                self._completeConversationClarification()
                self._logStage("CLARIFICATION", "Cleared stale pending intent")
                return None
            return self.askClarification(pendingIntent, self.pendingClarification.get("reason"))

        completedIntent = self._withUpdatedArgument(pendingIntent, missingParameter, value)
        validation = self.validateIntents([completedIntent])
        if not validation["success"]:
            self._storePendingClarification(completedIntent, validation["error"])
            return self.askClarification(completedIntent, validation["error"])

        self.pendingClarification = None
        self.lastClarification = None
        self._completeConversationClarification()
        self._logStage("CLARIFICATION", f"Resolved {missingParameter}")
        return self._executeValidatedIntents(
            baseSystemPrompt,
            userInput,
            [completedIntent],
            conversationHistory,
            confirmed=confirmed,
        )

    def _repairMissingArgumentFromInput(
        self,
        intents: list[StructuredIntent],
        error: str | None,
        userInput: str,
    ) -> list[StructuredIntent] | None:
        """Recover an omitted required argument when it is obvious in the same turn."""

        missingParameter = self._missingRequiredParameter(error)
        if not missingParameter or not intents:
            return None

        value = self._extractClarificationValue(userInput, missingParameter, allowBare=False)
        if value is None:
            return None

        repaired = list(intents)
        repaired[0] = self._withUpdatedArgument(repaired[0], missingParameter, value)
        return repaired

    def _storePendingClarification(self, intent: StructuredIntent, reason: str | None):
        """Remember one incomplete tool intent so the next short reply can finish it."""

        missingParameter = self._missingRequiredParameter(reason)
        clarificationManager = self._clarificationManager()
        question = self.askClarification(intent, reason)
        conversationId = self._clarificationConversationId()
        stored = None
        if clarificationManager is not None and hasattr(clarificationManager, "requestClarification"):
            try:
                stored = clarificationManager.requestClarification(
                    intent.asDict(),
                    question=question,
                    clarificationType=self._clarificationTypeForReason(reason, missingParameter),
                    requiredParameter=missingParameter,
                    conversationId=conversationId,
                    metadata={"reason": reason, "missingParameter": missingParameter},
                )
            except Exception as error:
                if self.logger:
                    self.logger.debug(f"Clarification manager request failed: {error}")

        if stored is not None:
            session = stored.get("session") if isinstance(stored, dict) else None
            request = stored.get("request") if isinstance(stored, dict) else None
            self.lastClarification = request.asDict() if hasattr(request, "asDict") else dict(request or {})
            self.pendingClarification = {
                "intent": intent,
                "missingParameter": missingParameter,
                "reason": reason,
                "sessionId": self._sessionIdFromValue(session if session is not None else stored.get("session")),
                "requestId": self.lastClarification.get("requestId", ""),
                "question": self.lastClarification.get("question", question),
                "clarificationType": self.lastClarification.get("clarificationType", self._clarificationTypeForReason(reason, missingParameter).value),
            }
        else:
            if not missingParameter:
                self.pendingClarification = None
                self.lastClarification = None
                return
            self.pendingClarification = {
                "intent": intent,
                "missingParameter": missingParameter,
                "reason": reason,
                "question": question,
                "clarificationType": self._clarificationTypeForReason(reason, missingParameter).value,
            }
        conversationManager = getattr(self.context, "conversationManager", None)
        if conversationManager is not None and hasattr(conversationManager, "startClarification") and stored is None:
            stored = conversationManager.startClarification(
                question,
                intent.asDict(),
                missingField=missingParameter,
            )
            session = stored.get("session") if isinstance(stored, dict) else None
            request = stored.get("request") if isinstance(stored, dict) else None
            self.lastClarification = request.asDict() if hasattr(request, "asDict") else dict(request or {})
            self.pendingClarification["sessionId"] = self._sessionIdFromValue(session if session is not None else stored.get("session"))
            self.pendingClarification["requestId"] = self.lastClarification.get("requestId", "")
            self.pendingClarification["question"] = self.lastClarification.get("question", question)
            self.pendingClarification["clarificationType"] = self.lastClarification.get("clarificationType", self._clarificationTypeForReason(reason, missingParameter).value)
        self._logStage("CLARIFICATION", f"Waiting for {missingParameter}")

    def _completeConversationClarification(self):
        """Notify the conversation manager that a pending clarification ended."""

        conversationManager = getattr(self.context, "conversationManager", None)
        if conversationManager is not None and hasattr(conversationManager, "completeClarification"):
            conversationManager.completeClarification()

    def _withUpdatedArgument(
        self,
        intent: StructuredIntent,
        parameter: str,
        value: Any,
    ) -> StructuredIntent:
        """Return a copy of an intent with one argument filled in."""

        arguments = dict(intent.arguments or {})
        arguments[parameter] = value
        return StructuredIntent(
            intent=intent.intent,
            arguments=arguments,
            confidence=intent.confidence,
            response=intent.response,
        )

    def _extractClarificationValue(
        self,
        userInput: str,
        parameter: str,
        allowBare: bool = True,
    ) -> Any | None:
        """Extract a simple deterministic value for a missing tool parameter."""

        text = str(userInput or "").strip()
        if not text:
            return None

        keyValue = re.search(
            rf"\b{re.escape(parameter)}\s*(?:=|:|is)\s*([A-Za-z0-9 _-]+)",
            text,
            flags=re.IGNORECASE,
        )
        if keyValue:
            return self._coerceClarificationValue(parameter, keyValue.group(1).strip(" .,!?'\""))

        if parameter == "room":
            roomFromDevicePhrase = self._extractRoomFromDevicePhrase(text)
            if roomFromDevicePhrase:
                return roomFromDevicePhrase

        if allowBare:
            bareValue = self._cleanBareClarification(text)
            if bareValue:
                return self._coerceClarificationValue(parameter, bareValue)
        return None

    @staticmethod
    def _extractRoomFromDevicePhrase(text: str) -> str | None:
        """Extract room names from phrases like 'my bedroom lights'."""

        match = re.search(
            r"\b(?:my|the|a|an)\s+([A-Za-z][A-Za-z0-9 _-]{0,40}?)\s+(?:lights?|lamps?)\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip(" .,!?'\"").lower() or None

        match = re.search(
            r"\b([A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2})\s+(?:lights?|lamps?)\b",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        room = match.group(1).strip(" .,!?'\"").lower()
        ignored = {"turn", "on", "off", "set", "dim", "brighten", "my", "the", "a", "an"}
        words = [word for word in room.split() if word not in ignored]
        return " ".join(words).strip() or None

    @staticmethod
    def _cleanBareClarification(text: str) -> str | None:
        """Clean a short clarification answer such as 'bedroom'."""

        cleaned = text.strip().strip(" .,!?'\"")
        cleaned = re.sub(r"^(it'?s|its|the|my|room is)\s+", "", cleaned, flags=re.IGNORECASE)
        tokenCount = len(cleaned.split())
        if tokenCount == 0 or tokenCount > 5:
            return None
        if "?" in cleaned:
            return None
        return cleaned.lower()

    @staticmethod
    def _coerceClarificationValue(parameter: str, value: str) -> Any:
        """Coerce common parameter types without using model inference."""

        if parameter in {"brightness", "level", "percent", "percentage"}:
            match = re.search(r"\d+", value)
            if match:
                return int(match.group(0))
        return value.strip().lower()

    @staticmethod
    def _missingRequiredParameter(error: str | None) -> str | None:
        """Parse the required parameter name from tool validation errors."""

        if not error:
            return None
        match = re.search(r"Missing required parameter:\s*([A-Za-z_][A-Za-z0-9_]*)", error)
        return match.group(1) if match else None

    @staticmethod
    def _isCancellation(userInput: str) -> bool:
        """Return whether the user is dismissing a pending clarification."""

        normalized = str(userInput or "").strip().lower()
        cancellationPhrases = {
            "cancel",
            "nevermind",
            "never mind",
            "don't worry",
            "dont worry",
            "forget it",
            "ignore it",
            "not now",
            "don't worry about it",
            "dont worry about it",
        }
        return any(phrase in normalized for phrase in cancellationPhrases)

    @staticmethod
    def _looksLikeNewConversation(userInput: str) -> bool:
        """Return whether text is likely a new request rather than a slot answer."""

        tokens = IntentPipeline._tokenize(userInput)
        if len(tokens) > 7:
            return True
        questionWords = {"what", "who", "when", "where", "why", "how"}
        return bool(tokens & questionWords)

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

        toolSchemas = self.tools.exportSchemas(offlineMode=self._isOfflineMode())
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
            self.tools.TOOL_INTENT_SCHEMA,
            conversationHistory,
        )
        if not response.success:
            return {"success": False, "error": response.error or "Intent parsing failed."}
        if not isinstance(response.rawResponse, dict):
            return {"success": False, "error": "Intent response was not a JSON object."}

        normalized = self.tools.normalizeIntentPayload(response.rawResponse)
        valid, error = ResponseValidator.validateSchema(normalized, self.tools.TOOL_INTENT_SCHEMA)
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

        return self.tools.validateIntent(intent, offlineMode=self._isOfflineMode())

    def validateIntents(self, intents: list[StructuredIntent]) -> dict[str, Any]:
        """Validate every non-conversation intent before executing the chain."""

        for intent in intents:
            validation = self.validateIntent(intent)
            if not validation["success"]:
                return validation
        return {"success": True, "error": None}

    def executeIntent(self, intent: StructuredIntent, confirmed: bool = False) -> dict[str, Any]:
        """Execute a validated intent through the deterministic tool executor."""

        return self.tools.executeIntent(
            intent,
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
            if self.tools.isConversationIntent(intent.intent):
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

    def _clarificationManager(self):
        manager = getattr(self.context, "clarificationManager", None)
        if manager is not None:
            return manager
        conversationManager = getattr(self.context, "conversationManager", None)
        if conversationManager is not None:
            return getattr(conversationManager, "clarifications", None)
        return None

    def _clarificationConversationId(self) -> str:
        conversationManager = getattr(self.context, "conversationManager", None)
        if conversationManager is not None:
            state = getattr(getattr(conversationManager, "context", None), "state", None)
            return str(getattr(state, "sessionId", "") or "")
        session = getattr(self.context, "sessionManager", None)
        if session is not None and hasattr(session, "currentSessionId"):
            return str(getattr(session, "currentSessionId", "") or "")
        return "default"

    @staticmethod
    def _clarificationTypeForReason(reason: str | None, missingParameter: str | None = None):
        from assistant.clarification.models import ClarificationType

        if missingParameter:
            if missingParameter in {"time", "start_time", "due_time"}:
                return ClarificationType.TIME_SELECTION
            if missingParameter in {"location", "room", "place"}:
                return ClarificationType.LOCATION_SELECTION
            if missingParameter in {"account", "email_account"}:
                return ClarificationType.ACCOUNT_SELECTION
            return ClarificationType.MISSING_PARAMETER
        if reason and "confidence" in reason.lower():
            return ClarificationType.LOW_CONFIDENCE
        return ClarificationType.MULTIPLE_OPTIONS if reason and "multiple" in reason.lower() else ClarificationType.MISSING_PARAMETER

    @staticmethod
    def _sessionIdFromValue(value) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            return str(value.get("sessionId") or "")
        return str(getattr(value, "sessionId", "") or "")

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
        if response.error:
            return f"I can't reach an available language provider right now. Last provider error: {response.error}"
        return "I couldn't interpret that request well enough to respond."

    def _isOfflineMode(self) -> bool:
        """Return whether the manager is in offline mode."""

        if hasattr(self.manager, "canUseStructuredOutput") and self.manager.canUseStructuredOutput():
            return False
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
        bridge_cache = getattr(self.context, "bridgeStateCache", None)
        if bridge_cache is not None and hasattr(bridge_cache, "snapshot"):
            try:
                cached = bridge_cache.snapshot()
                if isinstance(cached, dict):
                    state["bridge"] = cached
                    lights = cached.get("lights", [])
                    if isinstance(lights, list) and lights:
                        state["lights"] = lights
                    streams = cached.get("streams", [])
                    if isinstance(streams, list) and streams:
                        state["streams"] = streams
                    notifications = cached.get("notifications", [])
                    if isinstance(notifications, list) and notifications:
                        state["notifications"] = notifications
                    return state
            except Exception as error:
                if self.logger:
                    self.logger.debug(f"Bridge cache context unavailable: {error}")

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
        conversationManager = getattr(self.context, "conversationManager", None)
        if conversationManager is not None and hasattr(conversationManager, "recordAction"):
            conversationManager.recordAction(intent.intent, intent.arguments, execution)
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

    def _logStage(self, stage: str, message: str):
        """Log a readable structured pipeline stage."""

        line = f"[{stage}] {message}"
        if self.logger:
            self.logger.info(line)
        if self.rawLogger and hasattr(self.rawLogger, "logPipelineStage"):
            self.rawLogger.logPipelineStage(stage, message)
