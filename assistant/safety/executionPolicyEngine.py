"""Policy engine for Aura execution governance."""

from __future__ import annotations

from assistant.safety.models import ExecutionDecision, ExecutionRisk


class ExecutionPolicyEngine:
    """Apply deterministic safety rules to action requests."""

    HIGH_RISK_ACTIONS = {
        "unlock",
        "delete",
        "remove",
        "shutdown",
        "restart",
        "reload",
        "sendemail",
        "email.send",
        "automation.activate",
        "automation.resume",
        "automation.runnow",
    }

    CRITICAL_ACTIONS = {
        "system.shutdown",
        "system.restart",
        "system.reload",
        "security",
        "unlockdoor",
        "unlock.front.door",
    }

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Policy") if logger else None

    def apply(self, request, tool=None, permissionsOk: bool = True, trustScore: float = 1.0, rateLimited: bool = False, cooldownRemaining: float = 0.0, confirmed: bool = False):
        """Return a final execution decision."""

        if rateLimited:
            return ExecutionDecision(decision="RATE_LIMITED", reason="Execution rate limit exceeded.", riskLevel=self._riskFor(tool, request), cooldownRemaining=cooldownRemaining)

        risk = self._riskFor(tool, request)
        source = str(getattr(request, "source", "") or "").lower()
        metadata = getattr(request, "metadata", {}) or {}
        if hasattr(metadata, "asDict"):
            metadata = metadata.asDict()
        automation = source in {"automation", "automation_composer"} or bool((metadata or {}).get("automation", False))
        config = getattr(self.context, "config", None)
        requireHighRiskConfirmation = self._configBool(config, "safety.requireConfirmationForHighRisk", True)
        allowAutomationWithoutConfirmation = self._configBool(config, "safety.allowAutomationWithoutConfirmation", False)
        denyCriticalAutomation = self._configBool(config, "safety.denyCriticalAutomation", True)

        if not permissionsOk:
            return ExecutionDecision(decision="DENIED", reason="Missing required permission.", riskLevel=risk)

        if bool(getattr(tool, "confirmRequired", False)) and not confirmed:
            return ExecutionDecision(decision="REQUIRES_CONFIRMATION", reason="Action requires confirmation.", requiresConfirmation=True, riskLevel=risk)

        if risk == ExecutionRisk.CRITICAL and automation and denyCriticalAutomation and not confirmed:
            return ExecutionDecision(decision="DENIED", reason="Critical automation is not allowed.", riskLevel=risk)

        if automation and not allowAutomationWithoutConfirmation and risk in {ExecutionRisk.HIGH, ExecutionRisk.CRITICAL} and not confirmed:
            return ExecutionDecision(decision="REQUIRES_CONFIRMATION", reason="Automation requires explicit confirmation.", requiresConfirmation=True, riskLevel=risk)

        if risk in {ExecutionRisk.HIGH, ExecutionRisk.CRITICAL} and requireHighRiskConfirmation and not confirmed:
            return ExecutionDecision(decision="REQUIRES_CONFIRMATION", reason="High risk action requires confirmation.", requiresConfirmation=True, riskLevel=risk)

        if trustScore < 0.5 and not confirmed:
            return ExecutionDecision(decision="REQUIRES_CONFIRMATION", reason="Request trust is too low.", requiresConfirmation=True, riskLevel=risk)

        if risk == ExecutionRisk.MODERATE:
            return ExecutionDecision(decision="SAFE", reason="Moderate risk action approved.", riskLevel=risk)
        if risk == ExecutionRisk.LOW:
            return ExecutionDecision(decision="SAFE", reason="Action approved.", riskLevel=risk)
        return ExecutionDecision(decision="SAFE", reason="High risk action approved after validation.", riskLevel=risk)

    def _riskFor(self, tool, request) -> str:
        declared = ExecutionRisk.normalize(getattr(tool, "riskLevel", None))
        if declared != ExecutionRisk.LOW:
            return declared
        action = str(getattr(request, "action", "") or "").lower()
        if any(token in action for token in self.CRITICAL_ACTIONS):
            return ExecutionRisk.CRITICAL
        if any(token in action for token in self.HIGH_RISK_ACTIONS):
            return ExecutionRisk.HIGH
        if any(token in action for token in {"brightness", "color", "camera", "open", "launch", "notification"}):
            return ExecutionRisk.MODERATE
        return ExecutionRisk.LOW

    @staticmethod
    def _configBool(config, key: str, default: bool = False) -> bool:
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
