"""Tests for the Aura Developer UI infrastructure."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from interface.developerUI import DeveloperUI
from interface.developerUI.tracing import PerformanceTracker, UIEventTracer
from interface.developerUI.models import ConsoleEvent
from interface.developerUI.panels.systemPanel import SystemPanel
from interface.developerUI.state import DeveloperUIState
from interface.developerUI.subscriptions import UISubscriptionManager
from core.threading.events.eventManager import EventManager
from testing.tests.support.fakes import make_context


class DeveloperUITests(unittest.TestCase):
    """Validate developer UI state, tracing, and configuration behavior."""

    def setUp(self):
        self.context = make_context()
        self.context.config._data["developerUI"] = {
            "enabled": True,
            "refreshRate": 250,
            "maxEvents": 20,
            "verboseLogging": False,
            "traceEvents": True,
        }
        self.context.eventManager = EventManager(self.context)

    def test_state_tracks_voice_memory_errors_and_snapshots(self):
        state = DeveloperUIState(maxEvents=5)
        state.recordEvent(ConsoleEvent("voice.capture.started", {"source": "test"}))
        state.recordEvent(ConsoleEvent("voice.capture.finished", {"source": "test"}))
        state.recordEvent(ConsoleEvent("voice.transcription.completed", {"text": "hello aura", "audioDuration": 1.25}))
        state.recordEvent(ConsoleEvent("tts.started", {"text": "Hello"}))
        state.recordEvent(ConsoleEvent("tts.finished", {"success": True}))
        state.recordEvent(ConsoleEvent("provider.request.failed", {"error": "timeout"}))
        state.updateMemoryDebug(
            "[MEMORY RETRIEVAL]\n"
            "Retrieved: 12 memories\n"
            "Injected: 4 memories\n"
            "Filtered: 8 memories\n"
            "Score: 0.92"
        )

        snapshot = state.snapshot()

        self.assertEqual(snapshot.voice["mic"], "Idle")
        self.assertEqual(snapshot.voice["transcription"], "hello aura")
        self.assertEqual(snapshot.memory["retrieved"], 12)
        self.assertEqual(snapshot.memory["injected"], 4)
        self.assertEqual(snapshot.memory["topScore"], 0.92)
        self.assertEqual(len(snapshot.errors), 1)

    def test_event_tracer_wraps_event_manager_emit(self):
        state = DeveloperUIState(maxEvents=10)
        performance = PerformanceTracker()
        tracer = UIEventTracer(self.context, state, performance, traceEvents=True)

        tracer.install()
        try:
            self.context.eventManager.emit("voice.capture.started", {"source": "unit"})
        finally:
            tracer.uninstall()

        snapshot = state.snapshot()
        self.assertEqual(snapshot.events[-1]["name"], "voice.capture.started")
        self.assertEqual(snapshot.voice["mic"], "Recording")
        self.assertGreaterEqual(performance.snapshot()["aggregates"]["event"]["count"], 1)

    def test_subscription_manager_refreshes_observability_and_memory_debug(self):
        state = DeveloperUIState(maxEvents=10)
        self.context.memoryManager = type("MemoryStub", (), {"lastRetrievalDebug": "Retrieved: 2 memories\nInjected: 1 memories"})()
        self.context.observability = type(
            "ObservabilityStub",
            (),
            {
                "snapshot": lambda _self: {
                    "events": {"voice.capture.started": 1},
                    "modules": {"llm": {"loaded": True, "class": "LLMHandler"}},
                    "threads": [],
                    "scheduler": {"running": False},
                    "providers": {
                        "available": True,
                        "activeProvider": "gemini",
                        "activeModel": "gemini-2.5-flash",
                        "providers": {"gemini": {"active": True, "model": "gemini-2.5-flash"}},
                    },
                }
            },
        )()

        subscriptions = UISubscriptionManager(self.context, state)
        subscriptions.refreshSubsystemState()
        snapshot = state.snapshot()

        self.assertTrue(snapshot.providers["available"])
        self.assertEqual(snapshot.providers["activeProvider"], "gemini")
        self.assertEqual(snapshot.providers["activeModel"], "gemini-2.5-flash")
        self.assertEqual(snapshot.memory["retrieved"], 2)
        self.assertEqual(snapshot.memory["injected"], 1)
        self.assertIn("llm", snapshot.system["modules"])

    def test_system_panel_displays_active_llm_model(self):
        state = DeveloperUIState(maxEvents=10)
        state.updateSystem({"events": {}, "modules": {}})
        state.updateProviders(
            {
                "available": True,
                "activeProvider": "gemini",
                "activeModel": "gemini-2.5-flash",
                "providers": {"gemini": {"active": True, "model": "gemini-2.5-flash"}},
            }
        )

        lines = SystemPanel.buildLines(state.snapshot())

        self.assertIn("Active LLM: gemini (gemini-2.5-flash)", lines)

    def test_developer_ui_reads_config_and_initializes_without_window(self):
        developerUI = DeveloperUI(self.context)

        developerUI.initialize()
        try:
            self.assertTrue(developerUI.enabled)
            self.assertEqual(developerUI.refreshRate, 250)
            self.assertEqual(developerUI.maxEvents, 20)
            self.assertIs(self.context.developerUI, developerUI)
        finally:
            developerUI.shutdown()

    def test_direct_script_import_does_not_shadow_standard_logging(self):
        """Direct developer UI launches must not mask Python's stdlib logging module."""

        projectRoot = Path(__file__).resolve().parents[2]
        developerUiPath = projectRoot / "interface" / "developerUI"
        script = (
            "import sys; "
            f"sys.path.insert(0, {str(developerUiPath)!r}); "
            "import main; "
            "import logging; "
            "assert logging.INFO == 20, logging"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=projectRoot,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
