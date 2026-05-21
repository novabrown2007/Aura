"""Tests for Aura context awareness."""

import unittest
from datetime import datetime

from core.contextAwareness import ContextAwarenessManager
from core.threading.events.eventManager import EventManager
from tests.support.fakes import make_context


class _Cursor:
    """Small cursor stub."""

    def __init__(self, lastrowid=None):
        self.lastrowid = lastrowid


class _ContextDatabase:
    """In-memory context awareness persistence."""

    def __init__(self):
        self.signals = {}
        self.observations = []
        self.next_observation_id = 1

    def execute(self, query, params=()):
        normalized = " ".join(query.lower().split())

        if normalized.startswith("create table"):
            return _Cursor()

        if "insert into context_signals" in normalized:
            signal_name, value_json, first_seen_at, last_seen_at, changed_at, updated_at = params
            self.signals[signal_name] = {
                "signal_name": signal_name,
                "value_json": value_json,
                "first_seen_at": first_seen_at,
                "last_seen_at": last_seen_at,
                "changed_at": changed_at,
                "updated_at": updated_at,
            }
            return _Cursor()

        if normalized.startswith("update context_signals"):
            value_json, last_seen_at, changed_at, signal_name = params
            row = self.signals[signal_name]
            row["value_json"] = value_json
            row["last_seen_at"] = last_seen_at
            row["changed_at"] = changed_at
            return _Cursor()

        if "insert into context_observations" in normalized:
            signal_name, value_json, observed_at = params
            self.observations.append(
                {
                    "id": self.next_observation_id,
                    "signal_name": signal_name,
                    "value_json": value_json,
                    "observed_at": observed_at,
                }
            )
            self.next_observation_id += 1
            return _Cursor(self.next_observation_id - 1)

        return _Cursor()

    def fetchOne(self, query, params=()):
        normalized = " ".join(query.lower().split())
        if "from context_signals" in normalized:
            row = self.signals.get(params[0])
            return dict(row) if row else None
        return None

    def fetchAll(self, query, params=()):
        normalized = " ".join(query.lower().split())
        if "from context_signals" in normalized:
            return [dict(row) for row in self.signals.values()]
        return []


class _Scheduler:
    """Scheduler stub that records schedules."""

    def __init__(self):
        self.schedules = {}

    def getSchedule(self, name):
        return self.schedules.get(name)

    def addSchedule(self, schedule):
        self.schedules[schedule.name] = schedule


class ContextAwarenessTests(unittest.TestCase):
    """Validate context signal collection and change events."""

    def _create_manager(self):
        database = _ContextDatabase()
        context = make_context(database=database)
        context.eventManager = EventManager(context)
        context.scheduler = _Scheduler()
        manager = ContextAwarenessManager(context)
        return manager, context, database

    def test_collect_persists_provider_values_and_registers_schedule(self):
        manager, context, database = self._create_manager()
        manager.registerProvider("battery", lambda: {"percent": 82, "charging": True})

        observations = manager.collect(["battery"])

        self.assertEqual(observations["battery"]["value"]["percent"], 82)
        self.assertEqual(manager.getSignal("battery")["value"]["charging"], True)
        self.assertEqual(len(database.observations), 1)
        self.assertIn("context_awareness_poll", context.scheduler.schedules)

    def test_changed_signal_emits_generic_and_specific_events(self):
        manager, context, _database = self._create_manager()
        events = []
        context.eventManager.subscribe("context.changed", events.append)
        context.eventManager.subscribe("context.active_application.changed", events.append)

        manager.recordSignal("active_application", {"name": "PyCharm"})
        manager.recordSignal("active_application", {"name": "PyCharm"})
        manager.recordSignal("active_application", {"name": "Minecraft"})

        self.assertEqual(len(events), 4)
        self.assertEqual(events[-1].data["previous_value"]["name"], "PyCharm")
        self.assertEqual(events[-1].data["value"]["name"], "Minecraft")

    def test_seconds_since_changed_uses_changed_timestamp(self):
        manager, _context, database = self._create_manager()
        manager.recordSignal("desktop_activity", {"activity": "coding"})
        database.signals["desktop_activity"]["changed_at"] = "2026-05-21 10:00:00"

        seconds = manager.secondsSinceChanged(
            "desktop_activity",
            now=datetime(2026, 5, 21, 15, 0, 0),
        )

        self.assertEqual(seconds, 18000)

    def test_prompt_context_returns_compact_signal_values(self):
        manager, _context, _database = self._create_manager()
        manager.recordSignal("location", {"city": "Hamilton"})
        manager.recordSignal("music", {"playing": True, "artist": "Test"})

        prompt_context = manager.getPromptContext()

        self.assertEqual(prompt_context["location"]["city"], "Hamilton")
        self.assertEqual(prompt_context["music"]["playing"], True)


if __name__ == "__main__":
    unittest.main()
