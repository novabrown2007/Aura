"""Central execution governance for Aura."""

from __future__ import annotations

from assistant.safety.models import ExecutionDecision
from assistant.safety.actionValidator import ActionValidator
from assistant.safety.confirmationManager import ConfirmationManager
from assistant.safety.executionAuditLogger import ExecutionAuditLogger
from assistant.safety.executionGuard import ExecutionGuard
from assistant.safety.executionPolicyEngine import ExecutionPolicyEngine
from assistant.safety.handlers.safetyEventHandler import SafetyEventHandler
from assistant.safety.permissionManager import PermissionManager
from assistant.safety.rateLimitManager import RateLimitManager
from assistant.safety.trustEvaluator import TrustEvaluator


class SafetyManager:
    """Coordinate permissions, policies, confirmations, and rate limits."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety") if logger else None
        self.permissionManager = PermissionManager(context)
        self.policyEngine = ExecutionPolicyEngine(context)
        self.confirmationManager = ConfirmationManager(context)
        self.rateLimitManager = RateLimitManager(context, maxExecutionsPerMinute=int(self._configValue("safety.maxExecutionsPerMinute", 20)))
        self.actionValidator = ActionValidator(context)
        self.trustEvaluator = TrustEvaluator(context)
        self.auditLogger = ExecutionAuditLogger(context) if self._configBool("safety.auditLoggingEnabled", True) else None
        self.guard = ExecutionGuard(context, self)
        self.eventHandler = SafetyEventHandler(context, self)
        self.pendingConfirmations: dict[str, object] = {}
        self.enabled = bool(self._configBool("safety.safetyLayerEnabled", True))
        if self.context is not None:
            self.context.safetyManager = self
            self.context.permissionManager = self.permissionManager
            self.context.executionGuard = self.guard
            self.context.confirmationManager = self.confirmationManager
            self.context.rateLimitManager = self.rateLimitManager
            self.context.executionAuditLogger = self.auditLogger
            self.eventHandler.subscribe()

    def canExecute(self, request, tool=None, confirmed: bool = False, allowAdmin: bool = False):
        """Central execution decision gate."""

        if not self.enabled:
            return self.policyEngine.apply(request, tool=tool, confirmed=True)

        self._emit("action.requested", request.asDict() if hasattr(request, "asDict") else dict(request or {}))

        valid, error = self.actionValidator.validate(request, tool=tool)
        if not valid:
            decision = self._deny(
                request,
                "DENIED",
                error or "Invalid action.",
                tool=tool,
                metadata={"error": error},
            )
            return decision

        permissionsOk, missingPermissions, permissionRule = self.permissionManager.evaluate(request, tool=tool)
        if not permissionsOk:
            decision = self._deny(
                request,
                "DENIED",
                "Missing required permission.",
                tool=tool,
                metadata={
                    "missingPermissions": missingPermissions,
                    "rule": permissionRule.asDict() if permissionRule else {},
                },
            )
            return decision

        trustScore = self.trustEvaluator.evaluate(request, tool=tool)
        rateLimitEnabled = self._configBool("safety.executionRateLimitEnabled", True)
        cooldown = 0.0
        if rateLimitEnabled:
            allowed, cooldown = self.rateLimitManager.allow(request)
            if not allowed:
                decision = self._deny(
                    request,
                    "RATE_LIMITED",
                    "Execution rate limit exceeded.",
                    tool=tool,
                    metadata={"cooldownRemaining": cooldown},
                    cooldownRemaining=cooldown,
                )
                return decision

        decision = self.policyEngine.apply(
            request,
            tool=tool,
            permissionsOk=True,
            trustScore=trustScore,
            rateLimited=False,
            cooldownRemaining=0.0,
            confirmed=confirmed or bool((getattr(request, "metadata", {}) or {}).get("confirmed", False)),
        )

        if decision.decision == "REQUIRES_CONFIRMATION":
            confirmation = self.confirmationManager.requestConfirmation(
                request,
                decision,
                prompt=self._confirmationPrompt(request, decision),
                timeoutSeconds=int(self._configValue("safety.confirmationTimeoutSeconds", 60)),
            )
            self.pendingConfirmations[confirmation.requestId] = confirmation
            payload = decision.asDict()
            payload["confirmation"] = confirmation.asDict()
            payload["requestId"] = confirmation.requestId
            self._emit("execution.confirmation.required", payload)
            self._audit(request, decision, {"confirmation": confirmation.asDict()})
            return decision

        if decision.decision == "SAFE":
            self._emit("execution.allowed", decision.asDict())
        else:
            self._emit("execution.denied", decision.asDict())
        self._audit(request, decision)
        return decision

    def confirm(self, requestId: str, approved: bool = True):
        """Resolve a pending confirmation."""

        result = self.confirmationManager.confirm(requestId, approved=approved)
        if result is None:
            return None
        confirmation, accepted = result
        self.pendingConfirmations.pop(confirmation.requestId, None)
        request = confirmation.request
        metadata = dict(request.get("metadata") or {})
        metadata["confirmed"] = accepted
        request["metadata"] = metadata
        if not accepted:
            decision = self._deny(
                request,
                "DENIED",
                "Confirmation rejected.",
                metadata={"confirmation": confirmation.asDict()},
            )
            return decision
        requestObject = self._requestFromDict(request)
        executor = getattr(self.context, "toolExecutor", None)
        toolName = str(requestObject.action or "")
        if executor is not None and toolName:
            return executor.executeToolCall(
                toolName,
                requestObject.parameters,
                offlineMode=bool((getattr(requestObject.executionContext, "interface", {}) or {}).get("offlineMode", False)),
                confirmed=True,
                allowAdmin=bool((requestObject.metadata or {}).get("allowAdmin", False)),
            )
        return self.canExecute(requestObject, confirmed=True)

    def snapshot(self) -> dict:
        return {
            "available": True,
            "enabled": self.enabled,
            "pendingConfirmations": list(self.pendingConfirmations.keys()),
            "rateLimit": self.rateLimitManager.snapshot(),
            "confirmation": self.confirmationManager.snapshot(),
            "audit": self.auditLogger.snapshot() if self.auditLogger is not None else {"available": False},
        }

    def _deny(self, request, decisionName: str, reason: str, tool=None, metadata: dict | None = None, cooldownRemaining: float = 0.0):
        decision = ExecutionDecision(
            decision=decisionName,
            reason=reason,
            requiresConfirmation=decisionName == "REQUIRES_CONFIRMATION",
            riskLevel=self.policyEngine._riskFor(tool, request) if hasattr(self.policyEngine, "_riskFor") else "LOW",
            cooldownRemaining=cooldownRemaining,
            metadata=dict(metadata or {}),
        )
        self._emit(f"execution.{decisionName.lower()}", decision.asDict())
        self._audit(request, decision, metadata)
        return decision

    def _audit(self, request, decision, details: dict | None = None):
        if self.auditLogger is None:
            return
        try:
            self.auditLogger.log(request, decision, details or {})
        except Exception:
            pass

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Safety event emission failed for {eventName}: {error}")
        return None

    def _confirmationPrompt(self, request, decision) -> str:
        action = str(getattr(request, "action", "") or "action")
        return f"Please confirm {action}."

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    def _configBool(self, key: str, default: bool = False) -> bool:
        value = self._configValue(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _requestFromDict(values: dict):
        from assistant.safety.models import ExecutionContext, ExecutionRequest

        executionContext = values.get("executionContext") or {}
        if not isinstance(executionContext, ExecutionContext):
            executionContext = ExecutionContext(**dict(executionContext))
        return ExecutionRequest(
            requestId=str(values.get("requestId") or ""),
            source=str(values.get("source") or ""),
            module=str(values.get("module") or ""),
            action=str(values.get("action") or ""),
            parameters=dict(values.get("parameters") or {}),
            timestamp=str(values.get("timestamp") or ""),
            executionContext=executionContext,
            requestedBy=str(values.get("requestedBy") or ""),
            priority=str(values.get("priority") or "NORMAL"),
            metadata=dict(values.get("metadata") or {}),
        )

    def shutdown(self):
        """Release owned runtime hooks."""

        if getattr(self, "eventHandler", None) is not None:
            try:
                self.eventHandler.unsubscribe()
            except Exception:
                pass
        if getattr(self, "confirmationManager", None) is not None and hasattr(self.confirmationManager, "pending"):
            try:
                self.confirmationManager.pending.clear()
            except Exception:
                pass
        self.pendingConfirmations.clear()
