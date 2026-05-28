"""Thread-safe log file lifecycle and write management for Aura."""

from __future__ import annotations

import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class LogManager:
    """
    Manage Aura log directories, latest.log lifecycle, rotation, and writes.

    The manager owns all file I/O for both standard runtime logs and specialized
    streams such as LLM traces. Writes are protected by a lock per manager to
    prevent partial or interleaved entries in Aura's event-driven runtime.
    """

    SESSION_FORMAT = "%d-%m-%Y %H:%M:%S"
    FILE_TIMESTAMP_FORMAT = "%d-%m-%Y-%H:%M"

    def __init__(
        self,
        logPath: str | Path = "./logs/",
        llmLogPath: str | Path = "./logs/llm/",
        loggingEnabled: bool = True,
        consoleLoggingEnabled: bool = True,
        fileLoggingEnabled: bool = True,
        debugLoggingEnabled: bool = True,
    ):
        """Create a manager with configurable standard and LLM log paths."""

        self.logPath = Path(logPath or "./logs/")
        self.llmLogPath = Path(llmLogPath or "./logs/llm/")
        self.loggingEnabled = bool(loggingEnabled)
        self.consoleLoggingEnabled = bool(consoleLoggingEnabled)
        self.fileLoggingEnabled = bool(fileLoggingEnabled)
        self.debugLoggingEnabled = bool(debugLoggingEnabled)
        self.lock = threading.Lock()
        self.latestLogPath = self.logPath / "latest.log"
        self.latestLlmLogPath = self.llmLogPath / "latest.log"

        if self.loggingEnabled:
            self.initialize()

    @classmethod
    def fromConfig(cls, config=None):
        """Build a log manager from Aura config with stable defaults."""

        return cls(
            logPath=cls._getFirstConfigValue(config, ("logging.logPath", "logPath"), "./logs/"),
            llmLogPath=cls._getFirstConfigValue(
                config,
                ("logging.llmLogPath", "llmLogPath", "llm.logging.path"),
                "./logs/llm/",
            ),
            loggingEnabled=cls._getFirstConfigValue(
                config,
                ("logging.loggingEnabled", "loggingEnabled"),
                True,
            ),
            consoleLoggingEnabled=cls._getFirstConfigValue(
                config,
                ("logging.consoleLoggingEnabled", "consoleLoggingEnabled"),
                True,
            ),
            fileLoggingEnabled=cls._getFirstConfigValue(
                config,
                ("logging.fileLoggingEnabled", "fileLoggingEnabled"),
                True,
            ),
            debugLoggingEnabled=cls._getFirstConfigValue(
                config,
                ("logging.debugLoggingEnabled", "debugLoggingEnabled"),
                True,
            ),
        )

    def initialize(self):
        """Prepare standard and LLM log streams."""

        if not self.fileLoggingEnabled:
            return

        self._initializeStream(self.logPath, self.latestLogPath)
        self._initializeStream(self.llmLogPath, self.latestLlmLogPath)

    def appendLogEntry(self, entry: str):
        """Append one standard runtime log entry."""

        self._write(self.latestLogPath, entry)

    def appendLlmEntry(self, entry: str):
        """Append one detailed LLM trace entry."""

        self._write(self.latestLlmLogPath, entry)

    def writeConsole(self, entry: str):
        """Write to console when enabled, falling back silently on console errors."""

        if not self.loggingEnabled or not self.consoleLoggingEnabled:
            return
        try:
            print(entry)
        except Exception:
            pass

    def close(self):
        """Compatibility hook for shutdown; files are opened per append."""

        return None

    def _initializeStream(self, directory: Path, latestPath: Path):
        """Create a stream directory, rotate prior latest.log, and start a session."""

        with self.lock:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                if latestPath.exists():
                    self._rotateLatestLog(latestPath)
                self._writeUnlocked(latestPath, f"SESSION_START: {self._sessionTimestamp()}\n", mode="w")
            except Exception as error:
                self._fallbackPrint(f"Log initialization failed for {latestPath}: {error}")

    def _rotateLatestLog(self, latestPath: Path):
        """Rename a previous latest.log using the session start timestamp."""

        try:
            firstLine = ""
            with latestPath.open("r", encoding="utf-8", errors="replace") as file:
                firstLine = file.readline().strip()
            timestamp = self._timestampFromSessionLine(firstLine) or datetime.now()
            archivePath = latestPath.parent / f"{self._fileTimestamp(timestamp)}.log"
            archivePath = self._deduplicatePath(archivePath)
            latestPath.rename(archivePath)
        except Exception as error:
            self._fallbackPrint(f"Log rotation failed for {latestPath}: {error}")

    def _write(self, path: Path, entry: str):
        """Thread-safe append with safe failure handling."""

        if not self.loggingEnabled:
            return
        if not self.fileLoggingEnabled:
            return

        with self.lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                self._writeUnlocked(path, self._ensureTrailingNewline(entry), mode="a")
            except Exception as error:
                self._fallbackPrint(f"File logging failed for {path}: {error}")
                self._fallbackPrint(entry)

    @staticmethod
    def _writeUnlocked(path: Path, text: str, mode: str = "a"):
        """Write text without acquiring the manager lock."""

        with path.open(mode, encoding="utf-8", errors="replace") as file:
            file.write(text)

    @staticmethod
    def _timestampFromSessionLine(line: str) -> datetime | None:
        """Extract a datetime from a SESSION_START line."""

        match = re.match(r"^SESSION_START:\s*(.+)$", line or "")
        if not match:
            return None
        try:
            return datetime.strptime(match.group(1).strip(), LogManager.SESSION_FORMAT)
        except Exception:
            return None

    @classmethod
    def _fileTimestamp(cls, timestamp: datetime) -> str:
        """Return a filesystem-safe rotated log timestamp."""

        value = timestamp.strftime(cls.FILE_TIMESTAMP_FORMAT)
        if os.name == "nt":
            value = value.replace(":", "-")
        return value

    @classmethod
    def _sessionTimestamp(cls) -> str:
        """Return the startup timestamp written to latest.log."""

        return datetime.now().strftime(cls.SESSION_FORMAT)

    @staticmethod
    def _deduplicatePath(path: Path) -> Path:
        """Avoid overwriting an existing rotated log."""

        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        index = 1
        while True:
            candidate = parent / f"{stem}-{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    @staticmethod
    def _ensureTrailingNewline(entry: str) -> str:
        """Normalize log entries to one newline at write boundaries."""

        text = str(entry)
        return text if text.endswith("\n") else f"{text}\n"

    @staticmethod
    def _fallbackPrint(message: Any):
        """Last-resort logging path that must never raise."""

        try:
            print(message)
        except Exception:
            pass

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        """Read dot-path configuration from Aura config objects or dictionaries."""

        if config is None:
            return default
        if isinstance(config, dict):
            value = config
            for part in key.split("."):
                if not isinstance(value, dict) or part not in value:
                    return default
                value = value[part]
            return value
        try:
            if hasattr(config, "get"):
                return config.get(key, default)
        except TypeError:
            pass
        return default

    @classmethod
    def _getFirstConfigValue(cls, config, keys: tuple[str, ...], default=None):
        """Return the first configured value among several compatibility keys."""

        for key in keys:
            marker = object()
            value = cls._getConfigValue(config, key, marker)
            if value is not marker:
                return value
        return default
