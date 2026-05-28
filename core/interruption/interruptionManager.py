"""Global interruption coordinator for Aura."""

from __future__ import annotations

from time import perf_counter

from core.interruption.cancellationManager import CancellationManager
from core.interruption.events.interruptionEvents import InterruptionEvents
from core.interruption.handlers.actionInterruptionHandler import ActionInterruptionHandler
from core.interruption.handlers.conversationInterruptionHandler import ConversationInterruptionHandler
from core.interruption.handlers.providerInterruptionHandler import ProviderInterruptionHandler
from core.interruption.handlers.voiceInterruptionHandler import VoiceInterruptionHandler
from core.interruption.interruptionContext import InterruptionContext
from core.interruption.interruptionRegistry import InterruptionRegistry
from core.interruption.models.interruptionRequest import InterruptionRequest
from core.interruption.models.interruptionState import InterruptionState


class InterruptionManager:
    """Aura's central interruption coordinator."""

    VOICE_INTERRUPT = "VOICE_INTERRUPT"
    TTS_CANCEL = "TTS_CANCEL"
    ACTION_CANCEL = "ACTION_CANCEL"
    PROVIDER_CANCEL = "PROVIDER_CANCEL"
    CONVERSATION_CANCEL = "CONVERSATION_CANCEL"
    GLOBAL_CANCEL = "GLOBAL_CANCEL"

    DEFAULT_COMMANDS = {"stop", "cancel", "nevermind", "never mind", "pause", "shut up"}

    def __init__(self, context=None):
        self.context = context
        self.registry = InterruptionRegistry(context)
        self.cancellationManager = CancellationManager(context)
        self.state = InterruptionState()
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption") if logger else None
        self.enabled = self._getConfigBool("interruptions.interruptionsEnabled", True)
        self.voiceCommandsEnabled = self._getConfigBool("interruptions.interruptionVoiceCommandsEnabled", True)
        self.debugLogging = self._getConfigBool("interruptions.interruptionDebugLogging", True)
        self._registerDefaultHandlers()

    def initialize(self, context=None):
        """Bind to context and expose manager services."""

        if context is not None:
            self.context = context
        if self.context is not None:
            self.context.interruptionManager = self
            self.context.cancellationManager = self.cancellationManager
            self.context.interruptionRegistry = self.registry
        return self

    def requestInterruption(
        self,
        phrase: str = "",
        source: str = "runtime",
        interruptionType: str = GLOBAL_CANCEL,
        scope: str = "global",
        reason: str = "",
        metadata: dict | None = None,
    ) -> InterruptionContext:
        """Create and execute a global interruption request."""

        request = InterruptionRequest(
            interruptionType=interruptionType,
            source=source,
            phrase=phrase,
            scope=scope,
            reason=reason,
            metadata=metadata or {},
        )
        return self.handleRequest(request)

    def handleRequest(self, request: InterruptionRequest) -> InterruptionContext:
        """Route an interruption request through registry handlers."""

        context = InterruptionContext(request)
        if not self.enabled:
            return context

        started = perf_counter()
        self.state.start(request)
        self._emit(InterruptionEvents.REQUESTED, request.asDict())
        self._emit(InterruptionEvents.STARTED, context.asDict())
        if self.logger:
            self.logger.system(f"Interruption requested type={request.interruptionType} source={request.source} phrase={request.phrase!r}")

        self.cancellationManager.cancelAll()

        try:
            for operation in self.registry.getOperations(self._operationTypesForRequest(request)):
                self._cancelOperation(operation, context)

            for systemName, handler in self.registry.getHandlers().items():
                try:
                    for operationId in handler.cancel(context) or []:
                        context.markCancelled(operationId)
                        self._emit(InterruptionEvents.OPERATION_CANCELLED, {"operationId": operationId, "systemName": systemName})
                        self._emitSpecializedCancellation(systemName, operationId, context)
                except Exception as error:
                    context.markFailed(systemName, str(error))

            context.complete()
            self.state.cancelledOperations = list(context.interruptedOperations)
            self.state.failedOperations = list(context.failedOperations)
            self.state.complete()
            payload = context.asDict()
            payload["durationMs"] = (perf_counter() - started) * 1000.0
            self._emit(InterruptionEvents.COMPLETED, payload)
            if self.logger:
                self.logger.system(f"Interruption completed cancelled={len(context.interruptedOperations)} failed={len(context.failedOperations)}")
        except Exception as error:
            context.markFailed("interruption", str(error))
            self.state.failedOperations = list(context.failedOperations)
            self.state.complete()
            self._emit(InterruptionEvents.FAILED, context.asDict())
            if self.logger:
                self.logger.error(f"Interruption failed: {error}")
        return context

    def isInterruptionCommand(self, text: str) -> bool:
        """Return whether text is a high-priority interruption phrase."""

        if not self.enabled or not self.voiceCommandsEnabled:
            return False
        normalized = self.normalizeCommand(text)
        return normalized in self.DEFAULT_COMMANDS

    def handleVoiceCommand(self, text: str, source: str = "voice") -> InterruptionContext:
        """Handle a high-priority spoken interruption command."""

        return self.requestInterruption(
            phrase=text,
            source=source,
            interruptionType=self.VOICE_INTERRUPT,
            reason="voice interruption command",
        )

    @staticmethod
    def normalizeCommand(text: str) -> str:
        """Normalize a possible interruption command."""

        return " ".join(str(text or "").strip().lower().strip(" .,!?:;").split())

    def snapshot(self) -> dict:
        """Return interruption diagnostics."""

        return {
            "enabled": self.enabled,
            "voiceCommandsEnabled": self.voiceCommandsEnabled,
            "state": self.state.asDict(),
            "registry": self.registry.snapshot(),
        }

    def _cancelOperation(self, operation, interruptionContext):
        """Cancel one registered operation."""

        try:
            self.cancellationManager.cancel(operation.operationId)
            if operation.cancelHandler is not None:
                operation.cancelHandler(interruptionContext)
            interruptionContext.markCancelled(operation.operationId)
            self.registry.completeOperation(operation.operationId)
            self._emit(InterruptionEvents.OPERATION_CANCELLED, operation.asDict())
        except Exception as error:
            interruptionContext.markFailed(operation.operationId, str(error))

    def _operationTypesForRequest(self, request: InterruptionRequest) -> set[str] | None:
        """Return registry operation types affected by a request."""

        mapping = {
            self.TTS_CANCEL: {"tts", "playback", "speech"},
            self.PROVIDER_CANCEL: {"provider", "llm"},
            self.ACTION_CANCEL: {"action", "tool", "module"},
            self.CONVERSATION_CANCEL: {"conversation", "clarification"},
            self.VOICE_INTERRUPT: {"tts", "playback", "speech", "stt", "capture", "conversation", "provider", "action"},
            self.GLOBAL_CANCEL: None,
        }
        return mapping.get(request.interruptionType)

    def _emitSpecializedCancellation(self, systemName: str, operationId: str, interruptionContext):
        """Emit specialized cancellation events for common systems."""

        payload = {"operationId": operationId, "systemName": systemName, "interruption": interruptionContext.request.asDict()}
        if systemName == "voice" and ("tts" in operationId or "playback" in operationId):
            self._emit(InterruptionEvents.TTS_CANCELLED, payload)
        elif systemName == "provider":
            self._emit(InterruptionEvents.PROVIDER_CANCELLED, payload)
        elif systemName == "conversation":
            self._emit(InterruptionEvents.CONVERSATION_CANCELLED, payload)

    def _registerDefaultHandlers(self):
        """Register built-in subsystem handlers."""

        self.registry.registerHandler("voice", VoiceInterruptionHandler(self.context))
        self.registry.registerHandler("provider", ProviderInterruptionHandler(self.context))
        self.registry.registerHandler("action", ActionInterruptionHandler(self.context))
        self.registry.registerHandler("conversation", ConversationInterruptionHandler(self.context))

    def _emit(self, eventName: str, data: dict):
        """Emit an interruption event safely."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Interruption event emission failed for {eventName}: {error}")

    def _getConfigBool(self, key: str, default=False) -> bool:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
