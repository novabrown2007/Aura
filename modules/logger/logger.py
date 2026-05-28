"""Developer-facing Logger API for Aura."""

from __future__ import annotations

from datetime import datetime

from modules.logger.logManager import LogManager
from modules.logger.logTypes import LogTypes


class Logger:
    """
    Primary logging API used by Aura subsystems.

    Subsystems should create module-tagged instances, e.g.
    `Logger("WakeWordManager")`, and call the typed helpers instead of
    formatting timestamps or writing files themselves.
    """

    _defaultManager: LogManager | None = None

    def __init__(self, moduleName: str = "Aura", config=None, logManager: LogManager | None = None):
        """Create a logger for one module name."""

        self.moduleName = str(moduleName or "Aura")
        if logManager is not None:
            self.logManager = logManager
        elif config is not None:
            self.logManager = LogManager.fromConfig(config)
            Logger._defaultManager = self.logManager
        else:
            if Logger._defaultManager is None:
                Logger._defaultManager = LogManager()
            self.logManager = Logger._defaultManager

        self.logFilePath = self.logManager.latestLogPath

    def info(self, message: str):
        """Log an informational message."""

        self._log(LogTypes.INFO, message)

    def warn(self, message: str):
        """Log a warning message."""

        self._log(LogTypes.WARN, message)

    def warning(self, message: str):
        """Compatibility alias for warn."""

        self.warn(message)

    def error(self, message: str):
        """Log an error message."""

        self._log(LogTypes.ERROR, message)

    def debug(self, message: str):
        """Log a debug message when debug logging is enabled."""

        if self.logManager.debugLoggingEnabled:
            self._log(LogTypes.DEBUG, message)

    def system(self, message: str):
        """Log a system lifecycle message."""

        self._log(LogTypes.SYSTEM, message)

    def event(self, message: str):
        """Log an event bus or cross-system event message."""

        self._log(LogTypes.EVENT, message)

    def critical(self, message: str):
        """Compatibility alias that records critical failures as errors."""

        self.error(message)

    def getChild(self, name: str):
        """Return a child logger sharing this logger's manager."""

        childName = str(name or "").strip()
        if not childName:
            moduleName = self.moduleName
        elif self.moduleName and self.moduleName != "Aura":
            moduleName = f"{self.moduleName}.{childName}"
        else:
            moduleName = childName
        return Logger(moduleName, logManager=self.logManager)

    def close(self):
        """Close the underlying log manager."""

        self.logManager.close()

    def _log(self, logType: str, message: str):
        """Format and dispatch a standard log entry."""

        if not self.logManager.loggingEnabled:
            return

        entry = self._formatEntry(logType, message)
        self.logManager.writeConsole(entry)
        self.logManager.appendLogEntry(entry)

    def _formatEntry(self, logType: str, message: str) -> str:
        """Return the deterministic standard Aura log format."""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{logType}] [{self.moduleName}] {message}"


class AuraLogger(Logger):
    """
    Backward-compatible root logger name used by older Aura imports.

    New code should import `Logger` from `modules.logger.logger`.
    """

    def __init__(self, name: str = "Aura", level=None, logs_dir: str | None = None, config=None):
        """Create the root Aura logger, accepting legacy constructor options."""

        if logs_dir is not None and config is None:
            manager = LogManager(logPath=logs_dir, llmLogPath=str(logs_dir).rstrip("/\\") + "/llm")
            Logger._defaultManager = manager
            super().__init__(name, logManager=manager)
        else:
            super().__init__(name, config=config)

