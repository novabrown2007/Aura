"""Tests for the Aura Developer UI infrastructure."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import run_tests
from interface.developerUI import DeveloperUI
from interface.developerUI.tracing import PerformanceTracker, UIEventTracer
from interface.developerUI.models import ConsoleEvent, ConsoleStateSnapshot
from interface.developerUI.panels import (
    BridgePanel,
    ErrorPanel,
    EventPanel,
    IntentPanel,
    MemoryPanel,
    NotificationPanel,
    ProviderPanel,
    SessionPanel,
    SystemPanel,
    VoicePanel,
)
from interface.developerUI.rendering import LayoutManager, PanelRenderer
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

    def test_all_developer_panels_render_operator_snapshot_sections(self):
        """Every developer UI panel should render useful text from a state snapshot."""

        snapshot = ConsoleStateSnapshot(
            events=[
                {
                    "timestamp": "12:00:00.000",
                    "category": "voice",
                    "name": "voice.capture.started",
                    "source": "eventBus",
                    "summary": "source=unit",
                    "payload": {"source": "unit"},
                }
            ],
            sessions=[
                {
                    "sessionId": "session-1",
                    "interface": "windows",
                    "startedAt": "12:00:00.000",
                    "context": {"topic": "debug"},
                }
            ],
            intents=[
                {
                    "timestamp": "12:00:01.000",
                    "name": "intent.generated",
                    "payload": {
                        "intent": "lights.turnOn",
                        "confidence": 0.91,
                        "arguments": {"room": "bedroom"},
                        "status": "ready",
                    },
                }
            ],
            memory={
                "managerAvailable": True,
                "databasePath": "aura_memory.sqlite3",
                "storedCount": 1,
                "retrieved": 3,
                "injected": 2,
                "filtered": 1,
                "topScore": 0.92,
                "items": [
                    {
                        "category": "preferences",
                        "title": "Birthday",
                        "content": "Nova's birthday is March 22nd, 2007.",
                        "importance": 0.85,
                        "source": "profile.statement",
                    }
                ],
                "debugOutput": "Retrieved: 3 memories\nInjected: 2 memories",
            },
            voice={
                "mic": "Recording",
                "recording": True,
                "stt": "Processing",
                "tts": "Idle",
                "playback": "Idle",
                "transcription": "turn on the lights",
                "lastTiming": {"audioDuration": 1.25},
            },
            providers={
                "available": True,
                "activeProvider": "gemini",
                "activeModel": "gemini-2.5-flash",
                "fallbackProvider": "",
                "offlineMode": False,
                "providers": {"gemini": {"active": True, "model": "gemini-2.5-flash", "initialized": True}},
                "voice": {
                    "stt": {"provider": "faster-whisper", "model": "small.en", "enabled": True, "initialized": True},
                    "tts": {"provider": "piper", "model": "en_US-lessac-medium", "enabled": True, "initialized": False},
                },
            },
            bridge={
                "connected": True,
                "bridgeName": "Home Bridge",
                "subscriptions": ["lights.*"],
                "messages": [{"timestamp": "12:00:02.000", "name": "bridge.connected", "summary": "connected=True"}],
            },
            notifications=[
                {
                    "timestamp": "12:00:03.000",
                    "name": "notification.created",
                    "payload": {"priority": "normal", "source": "unit", "content": "Motion detected"},
                }
            ],
            errors=[
                {
                    "timestamp": "12:00:04.000",
                    "name": "provider.request.failed",
                    "payload": {"error": "quota"},
                    "error": "quota",
                }
            ],
            system={
                "uptimeSeconds": 10,
                "eventCount": 1,
                "events": {"voice.capture.started": 1},
                "modules": {"llm": {"loaded": True, "class": "LLMHandler"}},
            },
            performance={"aggregates": {"event": {"count": 1, "avgMs": 2.5}}},
        )
        expectedText = {
            EventPanel: "voice.capture.started",
            SessionPanel: "session-1",
            IntentPanel: "lights.turnOn",
            MemoryPanel: "Birthday",
            VoicePanel: "turn on the lights",
            ProviderPanel: "gemini-2.5-flash",
            BridgePanel: "Home Bridge",
            NotificationPanel: "Motion detected",
            ErrorPanel: "quota",
            SystemPanel: "Active LLM: gemini (gemini-2.5-flash)",
        }

        for panelClass, expected in expectedText.items():
            with self.subTest(panel=panelClass.__name__):
                panel = object.__new__(panelClass)
                rendered = []
                panel.setText = rendered.append

                panel.refresh(snapshot)

                self.assertTrue(rendered, panelClass.__name__)
                self.assertIn(expected, rendered[0])

    def test_layout_manager_registers_all_required_developer_panels(self):
        """The developer interface should keep every operational panel registered."""

        self.assertEqual(
            LayoutManager.panelClasses,
            (
                EventPanel,
                SessionPanel,
                IntentPanel,
                MemoryPanel,
                VoicePanel,
                ProviderPanel,
                BridgePanel,
                NotificationPanel,
                ErrorPanel,
                SystemPanel,
            ),
        )

    def test_panel_renderer_refreshes_remaining_panels_after_panel_failure(self):
        """A broken panel should not stop the whole developer interface refresh."""

        class FailingPanel:
            def refresh(self, _snapshot):
                raise RuntimeError("panel broke")

        class WorkingPanel:
            def __init__(self):
                self.refreshed = False

            def refresh(self, _snapshot):
                self.refreshed = True

        working = WorkingPanel()
        renderer = PanelRenderer([FailingPanel(), working], context=self.context)

        renderer.refresh(ConsoleStateSnapshot())

        self.assertTrue(working.refreshed)

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
        self.context.memoryManager = type(
            "MemoryStub",
            (),
            {
                "lastRetrievalDebug": "Retrieved: 2 memories\nInjected: 1 memories",
                "retrieveMemories": lambda _self, **_kwargs: [
                    SimpleNamespace(
                        category="preferences",
                        title="Relationship orientation",
                        content="Nova's relationship orientation is polyamorous.",
                        importance=0.85,
                        source="profile.statement",
                        updatedAt="2026-05-26T00:00:00+00:00",
                    )
                ],
            },
        )()
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
        self.assertEqual(snapshot.memory["storedCount"], 1)
        self.assertEqual(snapshot.memory["items"][0]["title"], "Relationship orientation")
        self.assertIn("llm", snapshot.system["modules"])

    def test_subscription_manager_reads_memory_store_without_retrieval_polling(self):
        """Developer UI refresh should not trigger scored retrieval on every tick."""

        state = DeveloperUIState(maxEvents=10)

        class MemoryStoreStub:
            def __init__(self):
                self.queryCalls = 0

            def queryMemories(self, query):
                self.queryCalls += 1
                self.lastLimit = query.limit
                return [
                    SimpleNamespace(
                        category="preferences",
                        title="Birthday",
                        content="Nova's birthday is March 22nd, 2007.",
                        importance=0.85,
                        source="profile.statement",
                        updatedAt="2026-05-26T00:00:00+00:00",
                    )
                ]

        class MemoryManagerStub:
            def __init__(self):
                self.store = MemoryStoreStub()
                self.lastRetrievalDebug = ""
                self.retrieveCalls = 0

            def retrieveMemories(self, **_kwargs):
                self.retrieveCalls += 1
                return []

        self.context.memoryManager = MemoryManagerStub()
        subscriptions = UISubscriptionManager(self.context, state)

        subscriptions.refreshSubsystemState()
        snapshot = state.snapshot()

        self.assertEqual(self.context.memoryManager.store.queryCalls, 1)
        self.assertEqual(self.context.memoryManager.store.lastLimit, 10)
        self.assertEqual(self.context.memoryManager.retrieveCalls, 0)
        self.assertEqual(snapshot.memory["storedCount"], 1)
        self.assertEqual(snapshot.memory["items"][0]["title"], "Birthday")

    def test_subscription_manager_subscribes_and_unsubscribes_all_default_events(self):
        """Developer UI event subscriptions should cover every advertised event once."""

        class EventManagerStub:
            def __init__(self):
                self.subscriptions = []
                self.unsubscriptions = []

            def subscribe(self, eventName, handler):
                self.subscriptions.append((eventName, handler))

            def unsubscribe(self, eventName, handler):
                self.unsubscriptions.append((eventName, handler))

        state = DeveloperUIState(maxEvents=10)
        eventManager = EventManagerStub()
        self.context.eventManager = eventManager
        subscriptions = UISubscriptionManager(self.context, state)

        subscriptions.subscribe()
        subscriptions.subscribe()
        subscriptions.unsubscribe()

        subscribedEvents = [eventName for eventName, _handler in eventManager.subscriptions]
        unsubscribedEvents = [eventName for eventName, _handler in eventManager.unsubscriptions]
        self.assertEqual(tuple(subscribedEvents), UISubscriptionManager.defaultEvents)
        self.assertEqual(tuple(unsubscribedEvents), UISubscriptionManager.defaultEvents)
        self.assertFalse(subscriptions.subscribed)

    def test_system_panel_displays_active_llm_model(self):
        state = DeveloperUIState(maxEvents=10)
        state.updateSystem({"events": {}, "modules": {}})
        state.updateProviders(
            {
                "available": True,
                "activeProvider": "gemini",
                "activeModel": "gemini-2.5-flash",
                "providers": {"gemini": {"active": True, "model": "gemini-2.5-flash"}},
                "voice": {
                    "stt": {"provider": "faster-whisper", "model": "small.en"},
                    "tts": {"provider": "piper", "model": "en_US-lessac-medium"},
                },
            }
        )

        lines = SystemPanel.buildLines(state.snapshot())

        self.assertIn("Active LLM: gemini (gemini-2.5-flash)", lines)
        self.assertIn("Active STT: faster-whisper (small.en)", lines)
        self.assertIn("Active TTS: piper (en_US-lessac-medium)", lines)

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

    def test_pycharm_run_configs_use_standard_windows_venv_interpreter(self):
        """PyCharm run configs should target the standard Windows venv interpreter."""

        projectRoot = Path(__file__).resolve().parents[2]
        configDir = projectRoot / ".idea" / "runConfigurations"
        configs = sorted(configDir.glob("*.xml"))

        self.assertTrue(configs, "Expected PyCharm run configurations to be present.")
        for configPath in configs:
            root = ET.parse(configPath).getroot()
            sdkHomeOptions = [
                option.get("value", "")
                for option in root.iter("option")
                if option.get("name") == "SDK_HOME"
            ]
            for sdkHome in sdkHomeOptions:
                self.assertNotIn("/.venv/python.exe", sdkHome, configPath.name)
                self.assertNotIn("\\.venv\\python.exe", sdkHome, configPath.name)
                self.assertIn(".venv/Scripts/python.exe", sdkHome.replace("\\", "/"), configPath.name)

    def test_pycharm_includes_dedicated_developer_ui_test_run_config(self):
        """PyCharm should expose a direct run config for developer UI tests."""

        projectRoot = Path(__file__).resolve().parents[2]
        configPath = projectRoot / ".idea" / "runConfigurations" / "Run_Developer_UI_tests.xml"

        self.assertTrue(configPath.exists())
        root = ET.parse(configPath).getroot()
        scriptNames = [
            option.get("value", "")
            for option in root.iter("option")
            if option.get("name") == "SCRIPT_NAME"
        ]
        self.assertIn("$PROJECT_DIR$/testing/tests/test_developer_ui.py", scriptNames)

    def test_interface_suite_includes_developer_ui_tests(self):
        """The shared interface-test run configuration should include developer UI coverage."""

        self.assertIn("testing.tests.interfaceTests", run_tests.SUITES["interfaces"])
        self.assertIn("testing.tests.test_developer_ui", run_tests.SUITES["interfaces"])
        self.assertEqual(run_tests.SUITES["developer_ui"], "testing.tests.test_developer_ui")

    def test_developer_application_runtime_launch_uses_project_root_working_directory(self):
        """Standalone developer UI startup should resolve config and memory paths from repo root."""

        projectRoot = Path(__file__).resolve().parents[2]
        developerUiDir = projectRoot / "interface" / "developerUI"
        script = "\n".join(
            [
                "from pathlib import Path",
                "from interface.developerUI.developerApplication import DeveloperApplication",
                "def fake_init(self, context, ownsRuntime=False):",
                "    print('cwd=' + str(Path.cwd()))",
                "    print('config=' + str(context.config.path.resolve()))",
                "    print('memory=' + str(context.memoryManager.store.databasePath.resolve()))",
                "    context.scheduler.stop()",
                "    context.memoryManager.shutdown()",
                "    context.llmManager.shutdown()",
                "    context.database.close()",
                "    context.logger.close()",
                "    raise SystemExit(0)",
                "DeveloperApplication.__init__ = fake_init",
                "DeveloperApplication.fromRuntime()",
            ]
        )

        env = dict(os.environ)
        env.setdefault("GEMINI_API_KEY", "test-key")
        env["PYTHONPATH"] = str(projectRoot)
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=developerUiDir,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn(f"cwd={projectRoot}", result.stdout)
        self.assertIn(f"config={projectRoot / 'config' / 'config.yml'}", result.stdout)
        self.assertIn(f"memory={projectRoot / 'aura_memory.sqlite3'}", result.stdout)


if __name__ == "__main__":
    unittest.main()
