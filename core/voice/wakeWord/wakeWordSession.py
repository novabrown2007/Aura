"""Wake word session and cooldown state."""

from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock

from .configuration import WakeWordConfig
from .models import WakeWordResult


class WakeWordSession:
    """Track activations and prevent duplicate wake word triggers."""

    def __init__(self, context=None, config: WakeWordConfig | None = None):
        self.context = context
        self.config = config or WakeWordConfig.fromContext(context)
        self.logger = context.logger.getChild("Voice.WakeWord.Session") if context and getattr(context, "logger", None) else None
        self._lock = Lock()
        self.activationCount = 0
        self.lastActivationAt: datetime | None = None
        self.cooldownUntil: datetime | None = None
        self.active = False
        self.inCooldown = False
        self.lastResult = WakeWordResult(phrase=self.config.wakeWordPhrase)

    def canActivate(self) -> bool:
        """Return whether a new activation is currently allowed."""

        with self._lock:
            self._refreshCooldownLocked()
            return not self.active and not self.inCooldown

    def beginActivation(self, result: WakeWordResult) -> bool:
        """Mark a wake activation as active if cooldown rules allow it."""

        with self._lock:
            self._refreshCooldownLocked()
            if self.active or self.inCooldown:
                return False
            self.active = True
            self.activationCount += 1
            self.lastActivationAt = datetime.now()
            self.lastResult = result
            if self.logger:
                self.logger.info(f"Wake word activation accepted at confidence={result.confidence:.3f}.")
            return True

    def startCooldown(self):
        """Start cooldown while the active voice turn is still in progress."""

        with self._lock:
            seconds = max(0.0, float(self.config.wakeWordCooldownSeconds))
            self.inCooldown = seconds > 0.0
            self.cooldownUntil = datetime.now() + timedelta(seconds=seconds) if seconds > 0.0 else None
            if self.logger:
                self.logger.info(f"Wake word cooldown started for {seconds:.1f}s.")

    def finishCooldown(self):
        """Force cooldown completion."""

        with self._lock:
            self.active = False
            self.inCooldown = False
            self.cooldownUntil = None
            if self.logger:
                self.logger.info("Wake word cooldown finished.")

    def cooldownRemainingSeconds(self) -> float:
        """Return seconds remaining in cooldown."""

        with self._lock:
            self._refreshCooldownLocked()
            if not self.inCooldown or self.cooldownUntil is None:
                return 0.0
            return max(0.0, (self.cooldownUntil - datetime.now()).total_seconds())

    def snapshot(self) -> dict:
        """Return a serializable state snapshot."""

        with self._lock:
            self._refreshCooldownLocked()
            cooldownRemaining = 0.0
            if self.inCooldown and self.cooldownUntil is not None:
                cooldownRemaining = max(0.0, (self.cooldownUntil - datetime.now()).total_seconds())
            return {
                "active": self.active,
                "inCooldown": self.inCooldown,
                "cooldownRemainingSeconds": cooldownRemaining,
                "activationCount": self.activationCount,
                "lastActivationAt": self.lastActivationAt.isoformat(timespec="seconds") if self.lastActivationAt else "",
                "lastResult": self.lastResult.asDict(),
            }

    def _refreshCooldownLocked(self):
        if self.inCooldown and self.cooldownUntil is not None and datetime.now() >= self.cooldownUntil:
            self.inCooldown = False
            self.cooldownUntil = None
