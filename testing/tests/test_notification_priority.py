"""Tests for Aura's assistant notification attention-management layer."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from assistant.notifications import (
    NotificationManager,
    NotificationPriority,
    NotificationPriorityEngine,
)
from assistant.notifications.models.notification import Notification
from interface.developerUI.models import ConsoleStateSnapshot
from interface.developerUI.panels import NotificationPanel
from core.threading.events.eventManager import EventManager
from testing.tests.support.fakes import make_context


class _NotificationStore:
    """Minimal notification persistence stub used by the tests."""

    def __init__(self):
        self.calls = []
        self.nextId = 1

    def createNotification(self, source_module, title, content, timestamp):
        self.calls.append(
            {
                "source_module": source_module,
                "title": title,
                "content": content,
                "timestamp": timestamp,
            }
        )
        notificationId = self.nextId
        self.nextId += 1
        return notificationId


class _InterruptionsStub:
    """Track interruption requests without running the full interruption stack."""

    def __init__(self):
        self.requests = []

    def requestInterruption(self, **kwargs):
        self.requests.append(dict(kwargs))
        return SimpleNamespace(asDict=lambda: dict(kwargs))


class _VoiceManagerStub:
    """Capture spoken notification text during delivery tests."""

    def __init__(self):
        self.spoken = []
        self.speechQueue = SimpleNamespace(_processing=False)

    def speakResponse(self, text):
        self.spoken.append(str(text))
        return SimpleNamespace(success=True, text=str(text))


class NotificationPriorityTests(unittest.TestCase):
    """Validate notification classification, routing, suppression, and UI state."""

    def _createContext(self):
        context = make_context()
        context.config._data["notifications"] = {
            "notificationsEnabled": True,
            "allowVoiceInterruptions": True,
            "criticalNotificationsAlwaysInterrupt": True,
            "notificationCooldownSeconds": 30,
            "maxQueuedNotifications": 50,
            "quietHoursEnabled": False,
            "quietHoursActive": False,
        }
        context.eventManager = EventManager(context)
        context.notifications = _NotificationStore()
        context.interruptionManager = _InterruptionsStub()
        context.voiceManager = _VoiceManagerStub()
        context.textToSpeech = SimpleNamespace(lastResult=None)
        context.speechQueue = context.voiceManager.speechQueue
        context.conversationManager = SimpleNamespace(
            snapshot=lambda: {
                "activeTopic": {"name": "lighting"},
                "activeEntity": {"name": "bedroom lights"},
                "pendingClarification": {"active": False},
            }
        )
        return context

    def test_priority_engine_classifies_security_alerts_by_context(self):
        """Motion at night should escalate more aggressively than motion in the day."""

        context = self._createContext()
        engine = NotificationPriorityEngine(context)

        morningPriority = engine.classifyPriority(
            "motion.detected",
            {
                "title": "Motion detected downstairs",
                "message": "Motion detected downstairs",
                "timestamp": "2026-05-29 14:00:00",
            },
            context,
        )
        nightPriority = engine.classifyPriority(
            "motion.detected",
            {
                "title": "Motion detected downstairs",
                "message": "Motion detected downstairs",
                "timestamp": "2026-05-29 03:00:00",
            },
            context,
        )
        smokePriority = engine.classifyPriority(
            "smoke.detected",
            {
                "title": "Smoke detected in the kitchen",
                "message": "Smoke detected in the kitchen",
            },
            context,
        )

        self.assertEqual(morningPriority, NotificationPriority.HIGH)
        self.assertEqual(nightPriority, NotificationPriority.CRITICAL)
        self.assertEqual(smokePriority, NotificationPriority.CRITICAL)

    def test_manager_delivers_high_priority_notifications_and_interrupts(self):
        """High-priority security alerts should trigger voice, UI, and interruption handling."""

        context = self._createContext()
        manager = NotificationManager(context)
        events = []
        context.eventManager.subscribe("notification.created", lambda event: events.append(event.name))
        context.eventManager.subscribe("notification.delivered", lambda event: events.append(event.name))
        context.eventManager.subscribe("notification.interrupted", lambda event: events.append(event.name))

        notification = manager.createNotification(
            {
                "title": "Motion detected downstairs",
                "message": "Motion detected downstairs",
                "source": "smartHome",
            },
            eventName="motion.detected",
        )

        self.assertIsInstance(notification, Notification)
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertGreaterEqual(len(context.notifications.calls), 1)
        self.assertTrue(context.interruptionManager.requests)
        self.assertIn("Motion detected downstairs", context.voiceManager.spoken[-1])
        self.assertIn("notification.created", events)
        self.assertIn("notification.delivered", events)
        self.assertIn("notification.interrupted", events)
        self.assertGreaterEqual(manager.history.snapshot()["count"], 2)

    def test_manager_suppresses_repeated_notifications_within_cooldown(self):
        """Repeated low-priority events should be throttled instead of spamming the user."""

        context = self._createContext()
        manager = NotificationManager(context)

        first = manager.createNotification(
            {
                "title": "Bedroom light disconnected",
                "message": "Bedroom light disconnected",
                "source": "smartHome",
            },
            eventName="home.light.disconnected",
        )
        second = manager.createNotification(
            {
                "title": "Bedroom light disconnected",
                "message": "Bedroom light disconnected",
                "source": "smartHome",
            },
            eventName="home.light.disconnected",
        )

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertGreaterEqual(len(manager.snapshot()["suppressedNotifications"]), 1)
        self.assertGreaterEqual(manager.history.snapshot()["count"], 2)

    def test_notification_panel_renders_notification_center_summary(self):
        """The developer UI should surface notification attention state, not just raw events."""

        snapshot = ConsoleStateSnapshot(
            notificationCenter={
                "enabled": True,
                "active": [{"title": "Motion detected downstairs", "priority": "HIGH", "source": "smartHome"}],
                "delivered": [{"title": "Motion detected downstairs", "priority": "HIGH", "source": "smartHome"}],
                "suppressed": [{"title": "Bedroom light disconnected", "priority": "LOW", "source": "smartHome"}],
                "escalated": [],
                "acknowledged": [],
                "interrupted": [],
                "queued": [],
                "history": {},
            }
        )

        panel = object.__new__(NotificationPanel)
        rendered = []
        panel.setText = rendered.append

        panel.refresh(snapshot)

        self.assertTrue(rendered)
        self.assertIn("State: enabled", rendered[0])
        self.assertIn("Motion detected downstairs", rendered[0])


if __name__ == "__main__":
    unittest.main()
