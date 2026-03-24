"""File-backed runtime logger for Aura."""

import logging
import os
from datetime import datetime
from pathlib import Path


class AuraLogger:
    """
    Provide Aura-wide logging through a per-run file in the `logs` directory.

    On initialization, the logger ensures a `logs` directory exists in the
    current project root, creates a new timestamped log file for the current
    process, and routes all log levels into that file.
    """

    def __init__(self, name="Aura", level=logging.INFO, logs_dir="logs"):
        """
        Initialize Aura's file-backed logger.

        Args:
            name (str):
                Root logger name.
            level (int):
                Logging level for the root logger.
            logs_dir (str):
                Directory used to store run-specific log files.
        """

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        self.logsDirectory = Path(logs_dir)
        self.logsDirectory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        self.logFilePath = self.logsDirectory / f"aura_{timestamp}_{os.getpid()}.log"

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        self._clearHandlers()

        file_handler = logging.FileHandler(self.logFilePath, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info("logger.py has been initialized.")

    def _clearHandlers(self):
        """
        Remove and close any existing handlers before creating a fresh run log.
        """

        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    def close(self):
        """
        Close all active logger handlers for clean shutdown and test cleanup.
        """

        self._clearHandlers()

    def debug(self, message: str):
        """Log a debug message."""

        self.logger.debug(message)

    def info(self, message: str):
        """Log an informational message."""

        self.logger.info(message)

    def warning(self, message: str):
        """Log a warning message."""

        self.logger.warning(message)

    def error(self, message: str):
        """Log an error message."""

        self.logger.error(message)

    def critical(self, message: str):
        """Log a critical error message."""

        self.logger.critical(message)

    def getChild(self, name: str):
        """
        Return a child logger that inherits the root file handler.
        """

        return self.logger.getChild(name)
