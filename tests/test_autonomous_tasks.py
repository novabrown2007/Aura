"""Tests for persistent autonomous assistant tasks."""

import unittest
from types import SimpleNamespace

from core.autonomy import AutonomousTaskManager
from core.threading.events.eventManager import EventManager
from tests.support.fakes import make_context


class _Cursor:
    """Small cursor stub with lastrowid support."""

    def __init__(self, lastrowid=None):
        self.lastrowid = lastrowid


class _AutonomousTaskDatabase:
    """In-memory autonomous task persistence stub."""

    def __init__(self):
        self.rows = []
        self.next_id = 1

    def execute(self, query, params=()):
        normalized = " ".join(query.lower().split())

        if normalized.startswith("create table"):
            return _Cursor()

        if "insert into autonomous_tasks" in normalized:
            task_id = self.next_id
            self.next_id += 1
            (
                name,
                task_type,
                description,
                status,
                interval_seconds,
                next_run_at,
                event_name,
                state,
                memory_context,
            ) = params
            self.rows.append(
                {
                    "id": task_id,
                    "name": name,
                    "task_type": task_type,
                    "description": description,
                    "status": status,
                    "interval_seconds": interval_seconds,
                    "next_run_at": next_run_at,
                    "last_run_at": None,
                    "event_name": event_name,
                    "state": state,
                    "memory_context": memory_context,
                    "created_at": "2026-05-21 00:00:00",
                    "updated_at": "2026-05-21 00:00:00",
                }
            )
            return _Cursor(task_id)

        if normalized.startswith("update autonomous_tasks set status = ?, next_run_at = ?"):
            status, next_run_at, task_id = params
            row = self._row(task_id)
            row["status"] = status
            row["next_run_at"] = next_run_at
            return _Cursor()

        if normalized.startswith("update autonomous_tasks set status = ?"):
            status, task_id = params
            self._row(task_id)["status"] = status
            return _Cursor()

        if normalized.startswith("update autonomous_tasks set state = ?"):
            state, task_id = params
            self._row(task_id)["state"] = state
            return _Cursor()

        if normalized.startswith("update autonomous_tasks set last_run_at = ?"):
            last_run_at, next_run_at, state, task_id = params
            row = self._row(task_id)
            row["last_run_at"] = last_run_at
            row["next_run_at"] = next_run_at
            row["state"] = state
            return _Cursor()

        return _Cursor()

    def fetchOne(self, query, params=()):
        normalized = " ".join(query.lower().split())
        if "order by id desc" in normalized:
            return {"id": self.rows[-1]["id"]} if self.rows else None
        if "from autonomous_tasks" in normalized:
            row = self._row(params[0])
            return dict(row) if row else None
        return None

    def fetchAll(self, query, params=()):
        normalized = " ".join(query.lower().split())
        if "from autonomous_tasks" in normalized:
            return [dict(row) for row in self.rows]
        return []

    def _row(self, task_id):
        for row in self.rows:
            if int(row["id"]) == int(task_id):
                return row
        return None


class _Scheduler:
    """Scheduler stub that records schedules."""

    def __init__(self):
        self.schedules = {}

    def getSchedule(self, name):
        return self.schedules.get(name)

    def addSchedule(self, schedule):
        self.schedules[schedule.name] = schedule


class AutonomousTaskManagerTests(unittest.TestCase):
    """Validate persistence, pause/resume, wakeups, and event dispatch."""

    def _create_manager(self):
        database = _AutonomousTaskDatabase()
        context = make_context(database=database)
        context.eventManager = EventManager(context)
        context.scheduler = _Scheduler()
        context.taskManager = None
        context.threader = None
        context.memoryManager = SimpleNamespace(getMemory=lambda: {"city": "Hamilton"})
        manager = AutonomousTaskManager(context)
        return manager, context, database

    def test_create_task_persists_state_and_registers_poll_schedule(self):
        manager, context, _database = self._create_manager()

        task = manager.createTask(
            name="Watch GPU prices",
            task_type="price.watch",
            interval_seconds=3600,
            state={"sku": "RTX 5090"},
            memory_context={"budget": 2000},
        )

        self.assertEqual(task["name"], "Watch GPU prices")
        self.assertEqual(task["state"]["sku"], "RTX 5090")
        self.assertEqual(task["memory_context"]["budget"], 2000)
        self.assertIn("autonomous_tasks_poll", context.scheduler.schedules)

    def test_pause_and_resume_update_status(self):
        manager, _context, _database = self._create_manager()
        task = manager.createTask("Check weather", "weather.check")

        paused = manager.pauseTask(task["id"])
        resumed = manager.resumeTask(task["id"], next_run_at="2026-05-21 12:00:00")

        self.assertEqual(paused["status"], "paused")
        self.assertEqual(resumed["status"], "active")
        self.assertEqual(resumed["next_run_at"], "2026-05-21 12:00:00")

    def test_due_task_runs_handler_and_updates_state(self):
        manager, _context, _database = self._create_manager()
        calls = []
        manager.registerHandler(
            "package.track",
            lambda payload: calls.append(payload) or {"delivered": False},
        )
        task = manager.createTask(
            "Track package",
            "package.track",
            next_run_at="2000-01-01 00:00:00",
            interval_seconds=60,
        )

        due = manager.wakeDueTasks()
        updated = manager.getTask(task["id"])

        self.assertEqual(len(due), 1)
        self.assertEqual(calls[0]["memory"]["city"], "Hamilton")
        self.assertEqual(updated["state"]["last_result"], {"delivered": False})
        self.assertIsNone(updated["state"]["last_error"])
        self.assertIsNotNone(updated["next_run_at"])

    def test_event_wakeup_dispatches_matching_active_tasks(self):
        manager, _context, _database = self._create_manager()
        calls = []
        manager.registerHandler("email.monitor", lambda payload: calls.append(payload))
        manager.createTask("Monitor email", "email.monitor", event_name="email.received")
        manager.createTask("Paused email", "email.monitor", event_name="email.received", status="paused")

        matching = manager.handleEventWakeup("email.received", {"from": "test@example.com"})

        self.assertEqual(len(matching), 1)
        self.assertEqual(calls[0]["reason"], "event")
        self.assertEqual(calls[0]["trigger_event"]["data"]["from"], "test@example.com")


if __name__ == "__main__":
    unittest.main()
