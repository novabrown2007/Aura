"""Context signal collection and change detection for Aura."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from typing import Callable

from core.threading.scheduler.schedule import Schedule


class ContextAwarenessManager:
    """
    Maintains Aura's current environment context.

    Signals are small snapshots such as current time, active applications,
    battery level, room occupancy, music state, desktop activity, notifications,
    or location. Providers can be registered by modules, interfaces, or tests.
    Each collection pass persists signal state and emits change events.
    """

    POLL_SCHEDULE_NAME = "context_awareness_poll"

    def __init__(self, context):
        """Initialize persistence, default providers, and scheduler hooks."""

        self.context = context
        self.database = getattr(context, "database", None)
        self.logger = context.logger.getChild("ContextAwareness") if getattr(context, "logger", None) else None
        self.providers: dict[str, Callable[[], object]] = {}

        self._initializeDatabase()
        self._registerDefaultProviders()
        self._registerPollingSchedule()

    def _initializeDatabase(self):
        """Ensure context signal persistence exists when a database is available."""

        if self.database is None:
            return

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS context_signals (
                signal_name VARCHAR(128) PRIMARY KEY,
                value_json TEXT NOT NULL,
                first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS context_observations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                signal_name VARCHAR(128) NOT NULL,
                value_json TEXT NOT NULL,
                observed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _registerDefaultProviders(self):
        """Register low-risk built-in providers."""

        self.registerProvider("time", self._timeProvider)
        self.registerProvider("active_applications", self._activeApplicationsProvider)

    def _registerPollingSchedule(self):
        """Register periodic context collection with the runtime scheduler."""

        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None or scheduler.getSchedule(self.POLL_SCHEDULE_NAME) is not None:
            return

        interval = 60.0
        config = getattr(self.context, "config", None)
        if config is not None:
            interval = float(config.get("context.poll_interval_seconds", interval))

        scheduler.addSchedule(
            Schedule(
                name=self.POLL_SCHEDULE_NAME,
                target=self.collect,
                interval=interval,
            )
        )

    def registerProvider(self, signal_name: str, provider: Callable[[], object]):
        """Register or replace a signal provider."""

        self.providers[str(signal_name)] = provider

    def collect(self, signal_names: list[str] | tuple[str, ...] | None = None):
        """Collect current values from signal providers and emit changes."""

        names = tuple(signal_names or self.providers.keys())
        observations = {}
        for name in names:
            provider = self.providers.get(name)
            if provider is None:
                continue
            try:
                observations[name] = self.recordSignal(name, provider())
            except Exception as exc:
                if self.logger:
                    self.logger.error(f"Context provider failed: {name} ({exc})")
        return observations

    def recordSignal(self, signal_name: str, value):
        """Persist one signal value and emit change events when it changes."""

        if self.database is None:
            return {
                "signal_name": signal_name,
                "value": value,
                "previous_value": None,
                "changed": True,
            }

        now = self._now()
        previous = self.getSignal(signal_name)
        value_json = self._encode(value)
        changed = previous is None or self._encode(previous["value"]) != value_json

        if previous is None:
            self.database.execute(
                """
                INSERT INTO context_signals (
                    signal_name, value_json, first_seen_at, last_seen_at,
                    changed_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (signal_name, value_json, now, now, now, now),
            )
        else:
            changed_at = now if changed else previous.get("changed_at")
            self.database.execute(
                """
                UPDATE context_signals
                SET value_json = ?, last_seen_at = ?, changed_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE signal_name = ?
                """,
                (value_json, now, changed_at, signal_name),
            )

        self.database.execute(
            """
            INSERT INTO context_observations (signal_name, value_json, observed_at)
            VALUES (?, ?, ?)
            """,
            (signal_name, value_json, now),
        )

        observation = {
            "signal_name": signal_name,
            "value": value,
            "previous_value": previous["value"] if previous else None,
            "changed": changed,
            "observed_at": now,
        }

        if changed:
            self._emit("context.changed", observation)
            self._emit(f"context.{signal_name}.changed", observation)

        return observation

    def getSignal(self, signal_name: str):
        """Return one persisted context signal."""

        if self.database is None:
            return None

        row = self.database.fetchOne(
            """
            SELECT signal_name, value_json, first_seen_at, last_seen_at,
                   changed_at, updated_at
            FROM context_signals
            WHERE signal_name = ?
            """,
            (signal_name,),
        )
        return self._prepareSignal(row)

    def getContext(self):
        """Return all current context signals keyed by signal name."""

        if self.database is None:
            return {}

        rows = self.database.fetchAll(
            """
            SELECT signal_name, value_json, first_seen_at, last_seen_at,
                   changed_at, updated_at
            FROM context_signals
            ORDER BY signal_name ASC
            """
        )
        return {
            signal["signal_name"]: signal
            for signal in (self._prepareSignal(row) for row in rows)
            if signal is not None
        }

    def getPromptContext(self):
        """Return compact context values suitable for LLM prompt enrichment."""

        return {
            name: signal["value"]
            for name, signal in self.getContext().items()
        }

    def secondsSinceChanged(self, signal_name: str, now: datetime | None = None):
        """Return seconds since a signal last changed."""

        signal = self.getSignal(signal_name)
        if signal is None or not signal.get("changed_at"):
            return None

        current = now or datetime.utcnow()
        changed_at = datetime.strptime(signal["changed_at"], "%Y-%m-%d %H:%M:%S")
        return max(0, int((current - changed_at).total_seconds()))

    def _timeProvider(self):
        """Return current UTC time metadata."""

        now = datetime.utcnow()
        return {
            "utc": self._format(now),
            "hour": now.hour,
            "weekday": now.strftime("%A"),
        }

    def _activeApplicationsProvider(self):
        """Return a conservative list of running process names on Windows."""

        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except Exception:
            return []

        if result.returncode != 0:
            return []

        names = []
        for line in result.stdout.splitlines():
            raw_name = line.split(",", 1)[0].strip().strip('"')
            if raw_name and raw_name not in names:
                names.append(raw_name)
        return names

    def _prepareSignal(self, row):
        if row is None:
            return None
        prepared = dict(row)
        prepared["value"] = self._decode(prepared.pop("value_json", None))
        return prepared

    def _emit(self, event_name: str, data: dict):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is not None:
            event_manager.emit(event_name, data)

    @staticmethod
    def _encode(value):
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _decode(value):
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    @classmethod
    def _now(cls):
        return cls._format(datetime.utcnow())

    @staticmethod
    def _format(value: datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
