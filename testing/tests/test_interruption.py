"""Tests for Aura's global interruption and cancellation infrastructure."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from core.interruption import InterruptionManager
from core.interruption.events import InterruptionEvents
from core.runtime.observability import ObservabilityManager
from interface.developerUI.models import ConsoleEvent
from interface.developerUI.state import DeveloperUIState
from testing.tests.support.fakes import make_context


class RecordingEventManager:
    """Collect emitted events for interruption tests."""

    def __init__(self):
        self.events = []

    def emit(self, eventName, data=None):
        self.events.append((eventName, data or {}))

    def listEvents(self):
        return sorted({name for name, _data in self.events})

    def listenerCount(self, eventName):
        return 0


class InterruptionTests(unittest.TestCase):
    """Validate global interruption routing and diagnostics."""

    def test_voice_command_cancels_registered_operations_and_handlers(self):
        cancelled = []
        context = make_context(extra={"eventManager": RecordingEventManager()})
        context.voiceManager = SimpleNamespace(
            speechQueue=SimpleNamespace(cancel=lambda: cancelled.append("queue")),
            textToSpeech=SimpleNamespace(cancel=lambda: cancelled.append("tts")),
            audioPlayer=SimpleNamespace(stopAudio=lambda: cancelled.append("playback")),
            pushToTalkManager=SimpleNamespace(cancelActiveCapture=lambda: True),
        )
        manager = InterruptionManager(context).initialize(context)
        manager.registry.registerOperation(
            "provider.request.unit",
            "provider",
            "provider",
            cancelHandler=lambda _ctx: cancelled.append("provider"),
        )

        result = manager.handleVoiceCommand("Stop.", source="unit")

        self.assertIn("provider.request.unit", result.interruptedOperations)
        self.assertIn("voice.speechQueue", result.interruptedOperations)
        self.assertIn("voice.tts", result.interruptedOperations)
        self.assertIn("voice.playback", result.interruptedOperations)
        self.assertIn("voice.capture", result.interruptedOperations)
        self.assertEqual(manager.registry.getOperations(), [])
        self.assertIn("queue", cancelled)
        self.assertIn("provider", cancelled)
        emitted = [name for name, _ in context.eventManager.events]
        self.assertIn(InterruptionEvents.REQUESTED, emitted)
        self.assertIn(InterruptionEvents.COMPLETED, emitted)
        self.assertIn(InterruptionEvents.OPERATION_CANCELLED, emitted)
        self.assertIn(InterruptionEvents.TTS_CANCELLED, emitted)

    def test_interruption_command_matching_is_exact_after_normalization(self):
        manager = InterruptionManager(make_context())

        self.assertTrue(manager.isInterruptionCommand("Never mind!"))
        self.assertTrue(manager.isInterruptionCommand("shut up"))
        self.assertFalse(manager.isInterruptionCommand("stop the timer"))

    def test_observability_and_developer_ui_expose_interruption_state(self):
        context = make_context(extra={"eventManager": RecordingEventManager()})
        manager = InterruptionManager(context).initialize(context)
        context.observability = ObservabilityManager(context)

        manager.requestInterruption(source="unit", phrase="cancel")
        snapshot = context.observability.snapshot()

        self.assertTrue(snapshot["interruptions"]["available"])
        self.assertTrue(snapshot["interruptions"]["enabled"])

        state = DeveloperUIState(maxEvents=10)
        for eventName, data in context.eventManager.events:
            state.recordEvent(ConsoleEvent(eventName, data))
        uiSnapshot = state.snapshot()

        self.assertFalse(uiSnapshot.interruptions["active"])
        self.assertEqual(uiSnapshot.interruptions["lastEvent"], InterruptionEvents.COMPLETED)


if __name__ == "__main__":
    unittest.main()
