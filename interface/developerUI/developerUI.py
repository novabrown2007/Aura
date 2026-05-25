"""Aura Developer UI manager."""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    projectRoot = Path(__file__).resolve().parents[2]
    if str(projectRoot) not in sys.path:
        sys.path.insert(0, str(projectRoot))

from interface.developerUI.logging import PerformanceTracker, UIEventTracer
from interface.developerUI.state import DeveloperUIState
from interface.developerUI.subscriptions import UISubscriptionManager


class DeveloperUI:
    """Coordinate developer UI state, subscriptions, tracing, and refresh lifecycle."""

    def __init__(self, context):
        self.context = context
        config = getattr(context, "config", None)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI") if logger else None
        self.enabled = self._bool(config, "developerUIEnabled", self._bool(config, "developerUI.enabled", True))
        self.refreshRate = self._int(config, "developerUIRefreshRate", self._int(config, "developerUI.refreshRate", 750))
        self.maxEvents = self._int(config, "developerUIMaxEvents", self._int(config, "developerUI.maxEvents", 500))
        self.verboseLogging = self._bool(config, "developerUIVerboseLogging", self._bool(config, "developerUI.verboseLogging", False))
        self.traceEvents = self._bool(config, "developerUITraceEvents", self._bool(config, "developerUI.traceEvents", True))
        self.state = DeveloperUIState(maxEvents=self.maxEvents)
        self.performanceTracker = PerformanceTracker()
        self.eventTracer = UIEventTracer(context, self.state, self.performanceTracker, traceEvents=self.traceEvents)
        self.subscriptions = UISubscriptionManager(context, self.state, self.eventTracer)
        self.initialized = False

    def initialize(self):
        """Initialize subscriptions and tracing."""

        if self.initialized:
            return
        if not self.enabled:
            if self.logger:
                self.logger.info("Developer UI disabled by configuration.")
            return
        self.eventTracer.install()
        self.subscriptions.subscribe()
        self.initialized = True
        self.context.developerUI = self
        if self.logger:
            self.logger.info("Developer UI initialized.")

    def refreshState(self):
        """Refresh non-event subsystem snapshots."""

        try:
            self.subscriptions.refreshSubsystemState()
            self.state.performance = self.performanceTracker.snapshot()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Developer UI state refresh failed: {error}")

    def shutdown(self):
        """Shutdown tracing and subscriptions safely."""

        try:
            self.subscriptions.unsubscribe()
        finally:
            self.eventTracer.uninstall()
            self.initialized = False
        if self.logger:
            self.logger.info("Developer UI shutdown complete.")

    @staticmethod
    def _value(config, key: str, default=None):
        if config is None:
            return default
        return config.get(key, default)

    @classmethod
    def _bool(cls, config, key: str, default=False):
        value = cls._value(config, key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _int(cls, config, key: str, default=0):
        try:
            return int(cls._value(config, key, default))
        except Exception:
            return int(default)


def main():
    """Standalone module entrypoint for the developer UI."""

    from interface.developerUI.developerApplication import DeveloperApplication

    DeveloperApplication.fromRuntime().run()


if __name__ == "__main__":
    main()
