"""Top-level execution coordinator."""

from __future__ import annotations

from assistant.execution.events import ExecutionEventHandler
from assistant.execution.executionAuditLogger import ExecutionAuditLogger
from assistant.execution.actionExecutor import ActionExecutor
from assistant.execution.executionPipeline import ExecutionPipeline
from assistant.execution.executionRegistry import ExecutionRegistry
from assistant.execution.executionResponseBuilder import ExecutionResponseBuilder
from assistant.execution.executionResultHandler import ExecutionResultHandler
from assistant.execution.executionRouter import ExecutionRouter
from assistant.execution.executionStateManager import ExecutionStateManager
from assistant.execution.executionValidator import ExecutionValidator
from assistant.execution.requests import ExecutionMetadata, ExecutionRequest


class ExecutionManager:
    """Central execution coordinator for Aura actions."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Execution") if logger else None
        self.enabled = bool(self._configBool("execution.executionPipelineEnabled", True))
        self.registry = ExecutionRegistry(context)
        self.stateManager = ExecutionStateManager(context)
        self.resultHandler = ExecutionResultHandler()
        self.responseBuilder = ExecutionResponseBuilder(context)
        self.validator = ExecutionValidator(context, registry=self.registry)
        self.router = ExecutionRouter(context)
        self.actionExecutor = ActionExecutor(context)
        self.auditLogger = ExecutionAuditLogger(context) if self._configBool("execution.executionAuditLoggingEnabled", True) else None
        self.pipeline = ExecutionPipeline(context, self.registry, self.validator, self.router, self.resultHandler, self.responseBuilder, self.stateManager, self.auditLogger, self.actionExecutor)
        self.eventHandler = ExecutionEventHandler(context, self)
        if self.context is not None:
            self.context.executionManager = self
        self.refreshRegistry()
        self.eventHandler.subscribe()

    def refreshRegistry(self):
        self.registry.entries.clear()
        self.registry.refreshFromToolRegistry()
        return self

    def executeToolCall(self, toolName: str, arguments: dict | None = None, offlineMode: bool = False, confirmed: bool = False, allowAdmin: bool = False, source: str = "SYSTEM", intent: str | None = None, conversationId: str = ""):
        tool = getattr(getattr(self.context, "toolRegistry", None), "getTool", lambda *_: None)(toolName)
        request = ExecutionRequest(
            intent=str(intent or toolName or ""),
            action=str(toolName or ""),
            parameters=dict(arguments or {}),
            source=str(source or "SYSTEM"),
            conversationId=str(conversationId or ""),
            requestedBy="assistant",
            metadata=ExecutionMetadata(
                modulesInvolved=[str(getattr(tool, "module", "") or "")] if tool is not None else [],
                permissions=list(getattr(tool, "requiredPermissions", ()) or []),
                confirmed=bool(confirmed),
                automation=str(source or "").upper() == "AUTOMATION",
            ),
        )
        if offlineMode:
            request.executionContext.runtimeContext["offlineMode"] = True
        if tool is not None and self._toolCategory(tool) == "ADMIN_ONLY" and not allowAdmin:
            denied = self.pipeline.resultHandler.normalize(
                request,
                result=None,
                status="DENIED",
                errors=[f"Tool requires admin permission: {toolName}"],
            )
            result = denied.asDict() if hasattr(denied, "asDict") else dict(denied or {})
            legacy = {
                "success": False,
                "toolName": toolName,
                "status": result.get("status", "DENIED"),
                "result": result.get("result"),
                "error": result.get("errors", ["Execution denied."])[0],
            }
            return legacy
        execution = self.execute(request, confirmed=confirmed, allowAdmin=allowAdmin, offlineMode=offlineMode, tool=tool)
        result = execution.asDict()
        legacy = {
            "success": result.get("status") == "COMPLETED",
            "toolName": toolName,
            "status": result.get("status"),
            "result": result.get("result"),
        }
        if result.get("status") == "REQUIRES_CONFIRMATION":
            legacy["requiresConfirmation"] = True
            legacy["error"] = result.get("errors", ["Confirmation required."])[0]
        if result.get("status") in {"FAILED", "DENIED", "TIMEOUT", "RATE_LIMITED"}:
            legacy["error"] = result.get("errors", ["Execution failed."])[0]
        return legacy

    def execute(self, request, confirmed: bool = False, allowAdmin: bool = False, offlineMode: bool = False, tool=None):
        if not self.enabled:
            return self.pipeline.resultHandler.normalize(request, result=None, status="DENIED", errors=["Execution pipeline disabled."])
        return self.pipeline.process(request, confirmed=confirmed, allowAdmin=allowAdmin, offlineMode=offlineMode, tool=tool)

    def executeRequest(self, request, confirmed: bool = False, allowAdmin: bool = False, offlineMode: bool = False, tool=None):
        return self.execute(request, confirmed=confirmed, allowAdmin=allowAdmin, offlineMode=offlineMode, tool=tool)

    def handleResolvedIntent(self, payload):
        return payload

    def handleConfirmation(self, payload):
        return self._confirmFromPayload(payload)

    def handleAutomationTriggered(self, payload):
        return payload

    def snapshot(self):
        return {
            "available": True,
            "enabled": self.enabled,
            "actions": self.registry.listActions(),
            "state": self.stateManager.snapshot(),
            "audit": self.auditLogger.snapshot() if self.auditLogger is not None else {"available": False},
        }

    def shutdown(self):
        if getattr(self, "eventHandler", None) is not None:
            try:
                self.eventHandler.unsubscribe()
            except Exception:
                pass

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

    def _confirmFromPayload(self, payload):
        safetyManager = getattr(self.context, "safetyManager", None)
        if safetyManager is None:
            return payload
        requestId = str((payload or {}).get("requestId") or "")
        if not requestId:
            return payload
        return safetyManager.confirm(requestId, approved=bool((payload or {}).get("approved", True)))

    def _configBool(self, key: str, default: bool = False) -> bool:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _toolCategory(tool) -> str:
        category = getattr(tool, "category", "")
        if hasattr(category, "value"):
            category = category.value
        return str(category or "").upper()
