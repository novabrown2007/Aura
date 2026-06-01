"""Deterministic execution pipeline."""

from __future__ import annotations

from time import perf_counter

from assistant.execution.actions import ActionStatus
from assistant.execution.actionExecutor import ActionExecutor


class ExecutionPipeline:
    """Process actions through validation, authorization, execution, and result handling."""

    stages = (
        "REQUESTED",
        "VALIDATING",
        "PERMISSION_CHECK",
        "EXECUTING",
        "PROCESSING_RESULT",
        "COMPLETED",
        "FAILED",
        "DENIED",
    )

    def __init__(self, context=None, registry=None, validator=None, router=None, resultHandler=None, responseBuilder=None, stateManager=None, auditLogger=None, actionExecutor=None):
        self.context = context
        self.registry = registry
        self.validator = validator
        self.router = router
        self.resultHandler = resultHandler
        self.responseBuilder = responseBuilder
        self.stateManager = stateManager
        self.auditLogger = auditLogger
        self.actionExecutor = actionExecutor or ActionExecutor(context)

    def process(self, request, confirmed: bool = False, allowAdmin: bool = False, offlineMode: bool = False, tool=None):
        started = perf_counter()
        actionDefinition = self.registry.getAction(getattr(request, "action", "")) if self.registry is not None else None
        state = self.stateManager.start(request) if self.stateManager is not None else None
        self._emit("execution.requested", request.asDict() if hasattr(request, "asDict") else dict(request or {}))
        if self.stateManager is not None:
            self.stateManager.update(request.requestId, ActionStatus.VALIDATING)
        valid, error = self.validator.validate(request, actionDefinition=actionDefinition)
        if not valid:
            response = self.resultHandler.normalize(request, result=None, errors=[error], status=ActionStatus.DENIED, metadata={"stage": "VALIDATING"})
            self._finalize(request, response, state, started, eventName="execution.denied")
            return response

        if offlineMode and actionDefinition is not None and not bool((getattr(actionDefinition, "metadata", {}) or {}).get("offlineAllowed", False)):
            response = self.resultHandler.normalize(
                request,
                result=None,
                errors=["Action is not available in offline mode."],
                status=ActionStatus.DENIED,
                metadata={"stage": "PERMISSION_CHECK", "offlineMode": True},
            )
            self._finalize(request, response, state, started, eventName="execution.denied")
            return response

        self._emit("execution.validated", {"requestId": request.requestId, "action": request.action})

        safetyManager = getattr(self.context, "safetyManager", None)
        if safetyManager is not None and hasattr(safetyManager, "canExecute"):
            decision = safetyManager.canExecute(request, tool=tool or self._toolFromDefinition(actionDefinition), confirmed=confirmed, allowAdmin=allowAdmin)
            if not decision.canExecute():
                status = getattr(decision, "decision", ActionStatus.DENIED)
                if getattr(decision, "requiresConfirmation", False):
                    status = "REQUIRES_CONFIRMATION"
                elif status not in {"RATE_LIMITED", ActionStatus.DENIED}:
                    status = ActionStatus.DENIED
                response = self.resultHandler.normalize(
                    request,
                    result={"decision": decision.asDict() if hasattr(decision, "asDict") else {}, "reason": getattr(decision, "reason", "")},
                    errors=[getattr(decision, "reason", "")] if getattr(decision, "reason", "") else [],
                    status=status,
                    metadata={"decision": decision.asDict() if hasattr(decision, "asDict") else {}},
                )
                eventName = "execution.denied"
                if status == "RATE_LIMITED":
                    eventName = "execution.rate_limited"
                elif status != ActionStatus.DENIED:
                    eventName = "execution.authorization.required"
                self._finalize(request, response, state, started, eventName=eventName)
                return response
        self._emit("execution.authorized", {"requestId": request.requestId, "action": request.action})
        if self.stateManager is not None:
            self.stateManager.update(request.requestId, ActionStatus.AUTHORIZED)

        if self.stateManager is not None:
            self.stateManager.update(request.requestId, ActionStatus.EXECUTING)
        self._emit("execution.started", {"requestId": request.requestId, "action": request.action})

        try:
            rawResult = self.actionExecutor.execute(request, actionDefinition, self.router, confirmed=confirmed, allowAdmin=allowAdmin)
            response = self.resultHandler.normalize(request, result=rawResult, status=ActionStatus.COMPLETED, metadata={"actionDefinition": actionDefinition.asDict() if actionDefinition is not None and hasattr(actionDefinition, "asDict") else {}})
            if self.responseBuilder is not None:
                response.metadata["assistantResponse"] = self.responseBuilder.build(request, response, actionDefinition=actionDefinition).asDict()
            self._finalize(request, response, state, started, eventName="execution.completed")
            return response
        except Exception as error:
            response = self.resultHandler.normalize(request, result=None, errors=[str(error)], status=ActionStatus.FAILED, metadata={"actionDefinition": actionDefinition.asDict() if actionDefinition is not None and hasattr(actionDefinition, "asDict") else {}})
            self._finalize(request, response, state, started, eventName="execution.failed")
            return response

    def _toolFromDefinition(self, actionDefinition):
        if actionDefinition is None:
            return None
        tool = type("ToolProxy", (), {})()
        tool.name = actionDefinition.actionName
        tool.module = actionDefinition.module
        tool.method = actionDefinition.executionHandler or actionDefinition.metadata.get("method", "")
        tool.category = actionDefinition.category
        tool.requiredPermissions = tuple(actionDefinition.requiredPermissions or ())
        tool.riskLevel = actionDefinition.riskLevel
        tool.validateArguments = lambda arguments: (True, None)
        tool.offlineAllowed = bool(actionDefinition.metadata.get("offlineAllowed", False))
        tool.confirmRequired = bool(actionDefinition.metadata.get("confirmRequired", False) or actionDefinition.riskLevel in {"HIGH", "CRITICAL"})
        return tool

    def _finalize(self, request, response, state, started, eventName: str):
        if self.stateManager is not None:
            self.stateManager.update(request.requestId, response.status, result=response.result)
        response.executionTime = perf_counter() - started
        self._emit(eventName, response.asDict())
        if self.auditLogger is not None:
            try:
                self.auditLogger.log(request, response, {"state": state.__dict__ if state is not None else {}})
            except Exception:
                pass

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload or {})
        except Exception:
            return None
