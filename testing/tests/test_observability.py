"""Tests for Aura runtime observability."""

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.runtime.observability import ObservabilityManager
from core.threading.events.eventManager import EventManager
from core.threading.scheduler.schedule import Schedule
from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from testing.tests.support.fakes import make_context


class _Threader:
    """Threading manager stub for diagnostics testing.tests."""

    def __init__(self):
        self.threads = {
            "worker": threading.Thread(name="worker", target=lambda: None, daemon=True)
        }
        self.controls = {
            "worker": SimpleNamespace(
                pause_event=SimpleNamespace(is_set=lambda: False),
                stop_event=SimpleNamespace(is_set=lambda: True),
            )
        }


class _Scheduler:
    """Scheduler stub for diagnostics testing.tests."""

    def __init__(self):
        self.running = True
        self.tick_interval = 1.0
        self.schedules = {
            "poll": Schedule(name="poll", target=lambda: None, interval=30.0)
        }


class ObservabilityTests(unittest.TestCase):
    """Validate snapshot sections and trace hooks."""

    def test_snapshot_reports_runtime_state(self):
        context = make_context()
        context.threader = _Threader()
        context.scheduler = _Scheduler()
        context.eventManager = EventManager(context)
        context.eventManager.subscribe("example.event", lambda event: None)
        context.memoryManager = SimpleNamespace(getMemory=lambda: {"user_name": "Nova"})
        context.toolRegistry = ToolRegistry(context)
        context.toolRegistry.registerTool(
            Tool(name="system.getTime", description="time", module="system", method="getTime")
        )
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            activeProviderName="ollama",
            fallbackProviderName="gemini",
            providers={
                "ollama": SimpleNamespace(initialized=True, model="gemma4:e4b"),
                "gemini": SimpleNamespace(initialized=False, model="gemini-2.5-flash"),
            },
        )
        context.modules = {"system": SimpleNamespace()}
        manager = ObservabilityManager(context)

        snapshot = manager.snapshot()

        self.assertEqual(snapshot["threads"][0]["name"], "worker")
        self.assertTrue(snapshot["threads"][0]["paused"])
        self.assertEqual(snapshot["events"]["example.event"], 1)
        self.assertEqual(snapshot["memory"]["keys"], ["user_name"])
        self.assertEqual(snapshot["tools"][0]["name"], "system.getTime")
        self.assertEqual(snapshot["providers"]["activeProvider"], "ollama")
        self.assertEqual(snapshot["providers"]["activeModel"], "gemma4:e4b")
        self.assertTrue(snapshot["providers"]["providers"]["ollama"]["active"])
        self.assertEqual(snapshot["providers"]["providers"]["gemini"]["model"], "gemini-2.5-flash")
        self.assertTrue(snapshot["modules"]["system"]["loaded"])
        self.assertEqual(snapshot["scheduler"]["schedules"][0]["name"], "poll")

    def test_provider_snapshot_uses_manager_status_when_available(self):
        context = make_context()
        context.llmManager = SimpleNamespace(
            getStatus=lambda: {
                "offlineMode": True,
                "activeProvider": "ollama",
                "activeModel": "gemma4:e4b",
                "preferredProvider": "gemini",
                "preferredModel": "gemini-2.5-flash",
                "fallbackProvider": "ollama",
                "offlineReason": "429 RESOURCE_EXHAUSTED",
                "canUseStructuredOutput": False,
            },
            providers={
                "ollama": SimpleNamespace(initialized=True, model="gemma4:e4b"),
                "gemini": SimpleNamespace(initialized=True, model="gemini-2.5-flash"),
            },
        )
        manager = ObservabilityManager(context)

        providers = manager.getProviders()

        self.assertTrue(providers["offlineMode"])
        self.assertEqual(providers["activeProvider"], "ollama")
        self.assertEqual(providers["preferredProvider"], "gemini")
        self.assertEqual(providers["offlineReason"], "429 RESOURCE_EXHAUSTED")
        self.assertFalse(providers["canUseStructuredOutput"])

    def test_event_and_tool_execution_record_traces(self):
        context = make_context()
        context.eventManager = EventManager(context)
        context.observability = ObservabilityManager(context)
        context.toolRegistry = ToolRegistry(context)
        context.toolExecutor = ToolExecutor(context)
        context.system = SimpleNamespace(ping=lambda value: f"pong:{value}")
        context.toolRegistry.registerTool(
            Tool(
                name="system.ping",
                description="Ping test tool.",
                parameters={"value": {"type": "string"}},
                requiredParameters=("value",),
                module="system",
                method="ping",
            )
        )

        context.eventManager.emit("example.event", {"value": 1})
        result = context.toolExecutor.executeToolCall("system.ping", {"value": "ok"})
        traces = context.observability.getTraces()

        self.assertTrue(result["success"])
        self.assertEqual(traces[0]["type"], "event")
        self.assertEqual(traces[0]["name"], "example.event")
        self.assertEqual(traces[-1]["type"], "tool")
        self.assertEqual(traces[-1]["status"], "completed")

    def test_logs_tail_current_log_file(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "aura.log"
            log_path.write_text("a\nb\nc\n", encoding="utf-8")
            context = make_context(extra={"logger": SimpleNamespace(logFilePath=log_path)})
            manager = ObservabilityManager(context)

            logs = manager.getLogs(lines=2)

            self.assertEqual(logs["path"], str(log_path))
            self.assertEqual(logs["lines"], ["b", "c"])


if __name__ == "__main__":
    unittest.main()
