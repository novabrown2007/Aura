"""Tests for Aura's local wake word activation layer."""

from __future__ import annotations

import sys
import time
import types
import unittest

import numpy as np

from core.voice.wakeWord import WakeWordManager
from core.voice.wakeWord.configuration import WakeWordConfig
from core.voice.wakeWord.events import WakeWordEvents
from core.voice.wakeWord.models import WakeWordResult
from core.voice.wakeWord.wakeWordDetector import WakeWordDetector
from interface.developerUI.state import DeveloperUIState
from interface.developerUI.models import ConsoleEvent
from testing.tests.support.fakes import make_context


class RecordingEventManager:
    """Collect wake word events emitted during tests."""

    def __init__(self):
        self.events = []

    def emit(self, eventName, data=None):
        self.events.append((eventName, data or {}))


class FakeOpenWakeWordModel:
    """Small OpenWakeWord stand-in that follows the Model.predict contract."""

    initCount = 0

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        FakeOpenWakeWordModel.initCount += 1

    def predict(self, frame):
        return {"hey_aura": 0.91, "noise": 0.02}


class FakePushToTalk:
    """Deterministic push-to-talk loop fake for wake activation tests."""

    def __init__(self):
        self.enabled = False
        self.started = False
        self.stopped = False
        self.lastResult = types.SimpleNamespace(errorMessage="")

    def startCapture(self):
        self.started = True
        return True

    def stopAndProcess(self):
        self.stopped = True
        return types.SimpleNamespace(success=True, errorMessage="")


class WakeWordTests(unittest.TestCase):
    """Validate wake word detection and event-driven activation behavior."""

    def setUp(self):
        self.context = make_context()
        self.context.eventManager = RecordingEventManager()
        self.context.config._data["voice"] = {
            "wakeWord": {
                "wakeWordEnabled": True,
                "wakeWordPhrase": "Hey Aura",
                "wakeWordPhrases": ["Aura", "Hey Aura", "Aura Wake"],
                "wakeWordSensitivity": 0.5,
                "wakeWordCooldownSeconds": 0,
                "wakeWordAutoStart": False,
                "wakeWordDebugLogging": True,
            }
        }

    def test_detector_initializes_openwakeword_once_and_detects_confidence(self):
        original_package = sys.modules.get("openwakeword")
        original_model = sys.modules.get("openwakeword.model")
        package = types.ModuleType("openwakeword")
        model_module = types.ModuleType("openwakeword.model")
        model_module.Model = FakeOpenWakeWordModel
        sys.modules["openwakeword"] = package
        sys.modules["openwakeword.model"] = model_module

        try:
            FakeOpenWakeWordModel.initCount = 0
            detector = WakeWordDetector(self.context, WakeWordConfig.fromContext(self.context))
            frame = np.zeros((1280,), dtype=np.int16)

            first = detector.initialize()
            second = detector.initialize()
            result = detector.processFrame(frame)

            self.assertIs(first, second)
            self.assertEqual(FakeOpenWakeWordModel.initCount, 1)
            self.assertTrue(result.detected)
            self.assertEqual(result.phrase, "hey_aura")
            self.assertEqual(result.modelName, "hey_aura")
            self.assertGreaterEqual(result.confidence, 0.9)
            self.assertGreaterEqual(result.predictionTimeMs, 0.0)
        finally:
            if original_package is None:
                sys.modules.pop("openwakeword", None)
            else:
                sys.modules["openwakeword"] = original_package
            if original_model is None:
                sys.modules.pop("openwakeword.model", None)
            else:
                sys.modules["openwakeword.model"] = original_model

    def test_config_supports_valid_wake_word_phrase_list(self):
        self.context.config._data["voice"]["wakeWord"]["wakeWordPhrase"] = "Hey Aura"
        self.context.config._data["voice"]["wakeWord"]["wakeWordPhrases"] = ["Aura", "Hey Aura", "Aura Wake"]

        config = WakeWordConfig.fromContext(self.context)

        self.assertEqual(config.validWakeWordPhrases(), ["Aura", "Hey Aura", "Aura Wake"])
        self.assertEqual(config.wakeWordPhrases, ["Aura", "Hey Aura", "Aura Wake"])
        self.assertTrue(config.isValidWakeWord("Hey Aura"))
        self.assertTrue(config.isValidWakeWord("Aura Wake"))
        self.assertFalse(config.isValidWakeWord("alexa"))

    def test_detector_ignores_predictions_outside_valid_phrase_list(self):
        config = WakeWordConfig.fromContext(self.context)
        config.wakeWordPhrases = ["Hey Aura"]

        modelName, confidence = WakeWordDetector._bestPrediction(
            {"alexa": 0.99, "hey_aura": 0.41},
            config.validWakeWordPhrases(),
        )

        self.assertEqual(modelName, "hey_aura")
        self.assertAlmostEqual(confidence, 0.41)

    def test_detector_uses_normalized_model_names_for_human_readable_phrases(self):
        config = WakeWordConfig.fromContext(self.context)
        config.wakeWordPhrases = ["Aura", "Hey Aura", "Aura Wake"]
        detector = WakeWordDetector(self.context, config)

        self.assertEqual(detector._wakeWordModels(), ["aura", "hey_aura", "aura_wake"])

    def test_manager_emits_wake_events_and_reuses_push_to_talk_pipeline(self):
        push = FakePushToTalk()
        self.context.pushToTalkManager = push
        config = WakeWordConfig.fromContext(self.context)
        config.wakeWordCaptureSeconds = 0.1
        manager = WakeWordManager(self.context, config)
        manager.initialized = True
        manager.listener.start = lambda: True
        manager.listener.resume = lambda: None

        manager.handleWakeWordDetected(
            WakeWordResult(detected=True, phrase="hey_aura", confidence=0.92, modelName="hey_aura")
        )
        time.sleep(0.35)

        emitted = [name for name, _ in self.context.eventManager.events]
        self.assertIn(WakeWordEvents.DETECTED, emitted)
        self.assertIn(WakeWordEvents.COOLDOWN_STARTED, emitted)
        self.assertIn(WakeWordEvents.COOLDOWN_FINISHED, emitted)
        self.assertTrue(push.started)
        self.assertTrue(push.stopped)
        self.assertFalse(push.enabled)

    def test_session_blocks_duplicate_activation_during_active_turn(self):
        push = FakePushToTalk()
        self.context.pushToTalkManager = push
        config = WakeWordConfig.fromContext(self.context)
        config.wakeWordCaptureSeconds = 0.25
        manager = WakeWordManager(self.context, config)
        manager.initialized = True
        manager.listener.start = lambda: True
        manager.listener.resume = lambda: None

        result = WakeWordResult(detected=True, phrase="hey_aura", confidence=0.92, modelName="hey_aura")
        manager.handleWakeWordDetected(result)
        manager.handleWakeWordDetected(result)
        time.sleep(0.45)

        detectedEvents = [name for name, _ in self.context.eventManager.events if name == WakeWordEvents.DETECTED]
        self.assertEqual(len(detectedEvents), 1)

    def test_developer_ui_tracks_wake_word_state_from_events(self):
        state = DeveloperUIState()
        state.recordEvent(ConsoleEvent(WakeWordEvents.LISTENING_STARTED, {"confidence": 0.1}))
        state.recordEvent(ConsoleEvent(WakeWordEvents.DETECTED, {"confidence": 0.93, "activationCount": 1}))
        state.recordEvent(ConsoleEvent(WakeWordEvents.COOLDOWN_STARTED, {"cooldownSeconds": 5}))

        wakeWord = state.snapshot().voice["wakeWord"]
        self.assertEqual(wakeWord["state"], "Cooldown")
        self.assertFalse(wakeWord["listening"])
        self.assertTrue(wakeWord["cooldown"])
        self.assertEqual(wakeWord["activationCount"], 1)
        self.assertAlmostEqual(wakeWord["confidence"], 0.93)


if __name__ == "__main__":
    unittest.main()
