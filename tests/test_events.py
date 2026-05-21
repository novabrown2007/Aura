"""Tests for Aura's event manager."""

import unittest

from core.threading.events.eventManager import EventManager
from core.threading.events.events import Event
from tests.support.fakes import make_context


class EventManagerTests(unittest.TestCase):
    """Validate pub/sub behavior for decoupled module communication."""

    def test_emit_accepts_event_name_and_payload(self):
        """Callers should be able to emit by name without constructing Event."""

        manager = EventManager(make_context())
        received = []
        manager.subscribe("lights.changed", received.append)

        event = manager.emit("lights.changed", {"device_id": "light1"})

        self.assertIsInstance(event, Event)
        self.assertEqual(event.name, "lights.changed")
        self.assertEqual(received[0].data["device_id"], "light1")

    def test_emit_returns_mutated_event_data(self):
        """Synchronous listeners can place small results back on the event."""

        manager = EventManager(make_context())
        manager.subscribe(
            "notifications.create",
            lambda event: event.data.update({"notification_id": 7}),
        )

        event = manager.emit("notifications.create", {"title": "A"})

        self.assertEqual(event.data["notification_id"], 7)


if __name__ == "__main__":
    unittest.main()
