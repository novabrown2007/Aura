"""Regression tests for Aura's unified personal schedule hub."""

from __future__ import annotations

import tempfile
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import unittest

from modules.personalSchedule import PersonalScheduleModule
from modules.personalSchedule.models import ScheduleItemType, ScheduleState
from modules.personalSchedule.scheduleManager import ScheduleManager
from testing.tests.support.fakes import make_context


class PersonalScheduleTests(unittest.TestCase):
    """Validate the unified schedule module and storage-backed manager."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.databasePath = Path(self.tempdir.name) / "schedule.sqlite3"
        self.events: list[tuple[str, dict]] = []
        self.cleanupTargets = []
        self.context = make_context()
        self.context.config._data["personalSchedule"] = {
            "personalScheduleEnabled": True,
            "scheduleNotificationsEnabled": True,
            "allowRecurringSchedules": True,
            "persistScheduleData": True,
            "scheduleTickIntervalSeconds": 1,
            "defaultReminderPriority": "NORMAL",
            "databasePath": str(self.databasePath),
        }
        self.context.eventManager = SimpleNamespace(
            emit=lambda name, payload=None: self.events.append((name, dict(payload or {}))),
            subscribe=lambda *args, **kwargs: None,
            unsubscribe=lambda *args, **kwargs: None,
        )
        self.context.notificationManager = SimpleNamespace(
            createNotification=lambda payload, eventName=None: {"payload": payload, "eventName": eventName}
        )
        self.context.scheduler = SimpleNamespace(
            schedules={},
            getSchedule=lambda name: self.context.scheduler.schedules.get(name),
            addSchedule=lambda schedule: self.context.scheduler.schedules.setdefault(schedule.name, schedule),
            removeSchedule=lambda name: self.context.scheduler.schedules.pop(name, None),
        )

    def tearDown(self):
        for target in reversed(self.cleanupTargets):
            shutdown = getattr(target, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    pass
        self.tempdir.cleanup()

    def test_module_exposes_unified_schedule_contract(self):
        module = PersonalScheduleModule(self.context)
        self.cleanupTargets.append(module)

        self.assertEqual(module.metadata.name, "personalSchedule")
        toolNames = {tool.name for tool in module.getTools()}
        self.assertTrue(toolNames)
        self.assertIn("schedule.createItem", toolNames)
        self.assertIn("schedule.createReminder", toolNames)
        self.assertIn("schedule.createTask", toolNames)
        self.assertIn("schedule.createTimer", toolNames)
        self.assertIn("schedule.completeTimer", toolNames)
        self.assertIn("schedule.getToday", toolNames)
        self.assertIn("schedule.getUpcoming", toolNames)
        self.assertIn("schedule.completeTimer", {action.name for action in module.getActions()})
        self.assertIn("schedule.tick", {subscription.eventName for subscription in module.getSubscriptions()})

    def test_manager_creates_and_queries_unified_items(self):
        manager = ScheduleManager(self.context).initialize()
        self.cleanupTargets.append(manager)
        todayStamp = datetime.utcnow().date().isoformat()

        reminder = manager.createReminder(title="Pay rent", dueTime=f"{todayStamp}T09:00:00")
        task = manager.createTask(title="Finish overlay", dueDate=f"{todayStamp}T12:00:00")
        timer = manager.createScheduleItem(
            title="Stretch",
            type=ScheduleItemType.TIMER,
            endTime=f"{todayStamp}T23:59:59",
        )
        bill = manager.createScheduleItem(
            title="Internet bill",
            type=ScheduleItemType.BILL,
            dueTime=f"{todayStamp}T18:00:00",
            priority="HIGH",
        )

        self.assertEqual(reminder.type, ScheduleItemType.REMINDER)
        self.assertEqual(task.type, ScheduleItemType.TASK)
        self.assertEqual(timer.type, ScheduleItemType.TIMER)
        self.assertEqual(bill.type, ScheduleItemType.BILL)

        today = manager.getTodaysSchedule()
        upcoming = manager.getUpcomingSchedule()
        search = manager.searchSchedule("overlay")

        self.assertGreaterEqual(today["count"], 4)
        self.assertGreaterEqual(upcoming["count"], 4)
        self.assertEqual(search[0].title, "Finish overlay")

    def test_manager_persists_items_across_restart(self):
        manager = ScheduleManager(self.context).initialize()
        self.cleanupTargets.append(manager)
        created = manager.createReminder(title="Call John", dueTime=f"{datetime.utcnow().date().isoformat()}T09:00:00")
        self.assertTrue(created.itemId)
        manager.shutdown()

        restartContext = make_context()
        restartContext.config._data["personalSchedule"] = self.context.config._data["personalSchedule"]
        restartContext.eventManager = self.context.eventManager
        restartContext.notificationManager = self.context.notificationManager
        restartContext.scheduler = self.context.scheduler

        restarted = ScheduleManager(restartContext).initialize()
        self.cleanupTargets.append(restarted)
        loaded = restarted.getScheduleItem(created.itemId)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Call John")

    def test_tick_processes_due_items_and_emits_events(self):
        manager = ScheduleManager(self.context).initialize()
        self.cleanupTargets.append(manager)
        timer = manager.createScheduleItem(
            title="Past timer",
            type=ScheduleItemType.TIMER,
            endTime="2000-01-01T00:00:00",
        )
        reminder = manager.createScheduleItem(
            title="Past reminder",
            type=ScheduleItemType.REMINDER,
            dueTime="2000-01-01T00:00:00",
        )

        result = manager.processTick()

        self.assertEqual(result["processed"], 2)
        self.assertEqual(manager.getScheduleItem(timer.itemId).state, ScheduleState.COMPLETED)
        self.assertEqual(manager.getScheduleItem(reminder.itemId).state, ScheduleState.COMPLETED)
        emittedNames = [name for name, _ in self.events]
        self.assertIn("timer.completed", emittedNames)
        self.assertIn("schedule.item.triggered", emittedNames)

    def test_complete_timer_marks_timer_completed(self):
        manager = ScheduleManager(self.context).initialize()
        self.cleanupTargets.append(manager)
        timer = manager.createTimer(title="Short timer", durationSeconds=60)

        completed = manager.completeTimer(timer.itemId)

        self.assertEqual(completed.state, ScheduleState.COMPLETED)
        self.assertEqual(manager.getScheduleItem(timer.itemId).state, ScheduleState.COMPLETED)


if __name__ == "__main__":
    unittest.main()
