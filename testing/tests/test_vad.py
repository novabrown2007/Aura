"""Tests for Aura voice activity detection and endpoint handling."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from core.runtime.observability import ObservabilityManager
from core.voice.vad import VADConfig, VADManager, VADResult, VADState
from core.voice.vad.silenceTracker import SilenceTracker
from interface.developerUI.models import ConsoleEvent
from interface.developerUI.state import DeveloperUIState
from interface.voice import VoiceManager
from testing.tests.support.fakes import make_context


class RecordingEventManager:
    """Collect emitted VAD events."""

    def __init__(self):
        self.events = []

    def emit(self, eventName, data=None):
        self.events.append((eventName, data or {}))

    def listEvents(self):
        return sorted({name for name, _ in self.events})

    def listenerCount(self, eventName):
        return 0


class FakeDetector:
    """Deterministic detector that returns preloaded speech results."""

    def __init__(self, results):
        self.results = list(results)
        self.initialized = False
        self.backend = "fake"
        self.lastError = ""
        self.lastResult = VADResult(backend="fake")
        self.resetCount = 0

    def initialize(self):
        self.initialized = True
        return True

    def reset(self):
        self.resetCount += 1

    def detect(self, audioFrame, sampleRate=None):
        result = self.results.pop(0) if self.results else VADResult(False, 0.0, backend="fake")
        self.lastResult = result
        return result

    def snapshot(self):
        return {
            "initialized": self.initialized,
            "backend": self.backend,
            "lastResult": self.lastResult.asDict(),
            "lastError": self.lastError,
        }


class FakeRecorder:
    """Recorder fake that exposes realtime chunk observation."""

    def __init__(self):
        self.handler = None
        self.recording = False
        self.lastError = ""

    def setAudioChunkHandler(self, handler):
        self.handler = handler

    def startRecording(self):
        self.recording = True
        return True

    def stopRecording(self):
        self.recording = False
        return True

    def saveRecording(self):
        return "fake.wav"

    def isRecording(self):
        return self.recording

    def cleanup(self):
        self.recording = False


class VADTests(unittest.TestCase):
    """Validate VAD state transitions, silence handling, and integrations."""

    def setUp(self):
        self.context = make_context()
        self.context.config._data["voice"] = {
            "STT": {"enabled": True, "sampleRate": 16000},
            "TTS": {"voiceEnabled": False},
            "pushToTalk": {"enabled": True},
            "vad": {
                "vadEnabled": True,
                "vadSilenceThresholdSeconds": 1.2,
                "vadSpeechThreshold": 0.5,
                "vadMinSpeechDuration": 0.3,
                "vadMaxRecordingDuration": 30,
                "vadDebugLogging": True,
            },
        }
        self.context.eventManager = RecordingEventManager()

    def test_silence_tracker_ignores_brief_pause(self):
        config = VADConfig(vadSilenceThresholdSeconds=1.2, vadMinSpeechDuration=0.3, vadMaxRecordingDuration=30)
        tracker = SilenceTracker(config)

        tracker.update(VADResult(True, 0.9, timestamp=0.0))
        tracker.update(VADResult(True, 0.9, timestamp=0.3))
        update = tracker.update(VADResult(False, 0.1, timestamp=0.4))
        self.assertFalse(update["endpointReached"])

        update = tracker.update(VADResult(False, 0.1, timestamp=1.7))
        self.assertTrue(update["endpointReached"])
        self.assertEqual(update["endpointReason"], "silence")

    def test_silence_tracker_timeout_prevents_endless_recording(self):
        config = VADConfig(vadSilenceThresholdSeconds=1.2, vadMinSpeechDuration=0.3, vadMaxRecordingDuration=2)
        tracker = SilenceTracker(config)

        tracker.update(VADResult(False, 0.0, timestamp=0.0))
        update = tracker.update(VADResult(False, 0.0, timestamp=2.1))

        self.assertTrue(update["endpointReached"])
        self.assertEqual(update["endpointReason"], "timeout")

    def test_vad_manager_emits_speech_silence_and_completion_events(self):
        config = VADConfig(vadSilenceThresholdSeconds=0.5, vadMinSpeechDuration=0.2, vadMaxRecordingDuration=5)
        detector = FakeDetector(
            [
                VADResult(True, 0.91, timestamp=0.0, backend="fake"),
                VADResult(True, 0.91, timestamp=0.3, backend="fake"),
                VADResult(False, 0.1, timestamp=0.4, backend="fake"),
                VADResult(False, 0.1, timestamp=1.0, backend="fake"),
            ]
        )
        manager = VADManager(self.context, config=config, detector=detector)

        manager.startSession(source="always_active")
        manager.processFrame(np.zeros((512,), dtype=np.int16), sampleRate=16000)
        manager.processFrame(np.zeros((512,), dtype=np.int16), sampleRate=16000)
        manager.processFrame(np.zeros((512,), dtype=np.int16), sampleRate=16000)
        manager.processFrame(np.zeros((512,), dtype=np.int16), sampleRate=16000)

        emitted = [name for name, _ in self.context.eventManager.events]
        self.assertIn("vad.started", emitted)
        self.assertIn("vad.speech.detected", emitted)
        self.assertIn("vad.silence.detected", emitted)
        self.assertIn("vad.speech.completed", emitted)
        self.assertIn("vad.finalizing", emitted)
        self.assertEqual(manager.stateManager.state, VADState.FINALIZING)

    def test_vad_manager_cancellation_resets_state(self):
        manager = VADManager(self.context, detector=FakeDetector([]))
        manager.startSession(source="always_active")

        self.assertTrue(manager.cancelSession(reason="test cancel"))

        self.assertEqual(manager.stateManager.state, VADState.IDLE)
        self.assertIsNone(manager.activeSession)

    def test_voice_manager_attaches_vad_to_automatic_capture(self):
        detector = FakeDetector([VADResult(True, 0.9, timestamp=0.0, backend="fake")])
        self.context.vadManager = VADManager(self.context, detector=detector)
        manager = VoiceManager(self.context)
        manager.recorder = FakeRecorder()

        self.assertTrue(manager.startVoiceCapture(source="always_active", vadControlled=True))
        self.assertIsNotNone(manager.recorder.handler)

        manager.recorder.handler(np.ones((512, 1), dtype=np.int16) * 2000, 16000)

        self.assertTrue(self.context.vadManager.snapshot()["speechDetected"])

    def test_developer_ui_tracks_vad_events(self):
        state = DeveloperUIState()

        state.recordEvent(ConsoleEvent("vad.started", {"enabled": True}))
        state.recordEvent(ConsoleEvent("vad.speech.detected", {"confidence": 0.92, "backend": "silero"}))
        state.recordEvent(ConsoleEvent("vad.silence.detected", {"silenceDuration": 0.4}))

        vad = state.snapshot().voice["vad"]
        self.assertEqual(vad["state"], "SILENCE_PENDING")
        self.assertTrue(vad["speechDetected"])
        self.assertTrue(vad["silenceDetected"])
        self.assertEqual(vad["backend"], "silero")

    def test_observability_exposes_vad_snapshot(self):
        self.context.vadManager = VADManager(self.context, detector=FakeDetector([]))
        self.context.observability = ObservabilityManager(self.context)

        snapshot = self.context.observability.snapshot()

        self.assertTrue(snapshot["vad"]["available"])
        self.assertTrue(snapshot["vad"]["enabled"])


if __name__ == "__main__":
    unittest.main()
