"""Tests for reviewable automation composition."""

import tempfile
import unittest
from pathlib import Path

from core.eventBus.autonomy import AutonomousTaskManager
from core.threading.events.eventManager import EventManager
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from modules.automation_composer import AutomationComposer
from modules.database.sqlite.sqliteDatabase import SQLiteDatabase
from testing.tests.support.fakes import make_context


class _Scheduler:
    """Scheduler stub that records schedules."""

    def __init__(self):
        self.schedules = {}

    def getSchedule(self, name):
        return self.schedules.get(name)

    def addSchedule(self, schedule):
        self.schedules[schedule.name] = schedule


class AutomationComposerTests(unittest.TestCase):
    """Validate automation drafts, activation, and execution."""

    def setUp(self):
        """Create an isolated runtime context."""

        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "aura-test.sqlite3"
        self.database = SQLiteDatabase(database_path=str(database_path))
        self.database.connect()
        self.database.initializeSchema()

        self.context = make_context(database=self.database)
        self.context.eventManager = EventManager(self.context)
        self.context.scheduler = _Scheduler()
        self.context.taskManager = None
        self.context.threader = None
        self.context.toolRegistry = ToolRegistry(self.context)
        self.context.toolExecutor = ToolExecutor(self.context)
        self.context.autonomousTasks = AutonomousTaskManager(self.context)
        self.composer = AutomationComposer(self.context)
        self.context.automationComposer = self.composer

    def tearDown(self):
        """Close temporary resources."""

        self.database.close()
        self.temp_dir.cleanup()

    def test_create_draft_persists_reviewable_plan(self):
        """Drafts should store trigger, actions, conditions, and safety notes."""

        plan = self.composer.createDraft(
            name="Morning briefing",
            goal="Tell me what matters each morning.",
            trigger_type="interval",
            trigger_value="3600",
            conditions=[{"type": "always"}],
            actions=[
                {
                    "type": "event",
                    "name": "notifications.create",
                    "data": {
                        "title": "Briefing",
                        "content": "Time to review the day.",
                        "timestamp": "2026-05-24 09:00:00",
                    },
                }
            ],
            safety={"requires_review": True},
        )

        self.assertEqual(plan["status"], "draft")
        self.assertEqual(plan["trigger_type"], "interval")
        self.assertEqual(plan["actions"][0]["name"], "notifications.create")
        self.assertTrue(plan["safety"]["requires_review"])

    def test_activate_plan_creates_autonomous_task(self):
        """Activation should delegate scheduling to AutonomousTaskManager."""

        plan = self.composer.createDraft(
            name="Watch inbox",
            goal="React when an email arrives.",
            trigger_type="event",
            trigger_value="email.received",
            actions=[{"type": "event", "name": "notifications.create", "data": {"title": "Mail"}}],
        )

        active = self.composer.activatePlan(plan["id"])
        task = self.context.autonomousTasks.getTask(active["autonomous_task_id"])

        self.assertEqual(active["status"], "active")
        self.assertEqual(task["task_type"], "automation_composer.execute")
        self.assertEqual(task["event_name"], "email.received")
        self.assertEqual(task["memory_context"]["automation_plan_id"], plan["id"])

    def test_event_trigger_runs_plan_actions(self):
        """Event-triggered automations should run their configured actions."""

        received = []
        self.context.eventManager.subscribe(
            "notifications.create",
            lambda event: received.append(dict(event.data)),
        )
        plan = self.composer.createDraft(
            name="Door alert",
            goal="Notify me when the door opens.",
            trigger_type="event",
            trigger_value="door.opened",
            actions=[
                {
                    "type": "event",
                    "name": "notifications.create",
                    "data": {"title": "Door", "content": "The door opened."},
                }
            ],
        )
        self.composer.activatePlan(plan["id"])

        matching = self.context.autonomousTasks.handleEventWakeup("door.opened", {"room": "front"})
        updated = self.composer.getPlan(plan["id"])

        self.assertEqual(len(matching), 1)
        self.assertEqual(received[0]["title"], "Door")
        self.assertEqual(received[0]["trigger_event"]["data"]["room"], "front")
        self.assertFalse(updated["last_result"]["skipped"])

    def test_pause_plan_pauses_backing_task(self):
        """Pausing a plan should stop the backing autonomous task."""

        plan = self.composer.createDraft(
            name="Hourly note",
            goal="Send an hourly note.",
            trigger_type="interval",
            trigger_value="3600",
            actions=[{"type": "event", "name": "notifications.create", "data": {"title": "Ping"}}],
        )
        active = self.composer.activatePlan(plan["id"])

        paused = self.composer.pausePlan(plan["id"])
        task = self.context.autonomousTasks.getTask(active["autonomous_task_id"])

        self.assertEqual(paused["status"], "paused")
        self.assertEqual(task["status"], "paused")


if __name__ == "__main__":
    unittest.main()
