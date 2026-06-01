"""Coverage contract tests for Aura source areas and runtime tools."""

from __future__ import annotations

import ast
import py_compile
from pathlib import Path
import unittest

import run_tests


class CoverageContractTests(unittest.TestCase):
    """Guard against adding source features or tools without test ownership."""

    root = Path(__file__).resolve().parents[2]
    excludedParts = {".venv", "venv", "__pycache__", ".git", ".idea", "build", "dist", "logs"}
    sourceRoots = {"assistant", "bridge", "config", "core", "interface", "modules", "providers", "scripts"}
    testedFeatureAreas = {
        "bridge": ("testing/tests/test_bridge_protocol.py",),
        "assistant": ("testing/tests/test_architecture.py",),
        "assistant/clarification": ("testing/tests/test_clarification.py",),
        "assistant/execution": ("testing/tests/test_execution_pipeline.py",),
        "assistant/safety": ("testing/tests/test_safety_layer.py",),
        "assistant/memory": ("testing/tests/test_semantic_memory.py",),
        "assistant/notifications": ("testing/tests/test_notification_priority.py",),
        "config": ("testing/tests/test_config_loader.py",),
        "core/conversation": ("testing/tests/test_conversation_continuity.py",),
        "core/engine.py": ("testing/tests/test_runtime_smoke.py",),
        "core/eventBus/event.py": ("testing/tests/test_events.py",),
        "core/eventBus/autonomy": ("testing/tests/test_autonomous_tasks.py",),
        "core/interruption": ("testing/tests/test_interruption.py",),
        "core/personality": ("testing/tests/test_personality.py",),
        "core/modules": ("testing/tests/test_module_framework.py",),
        "core/router": ("testing/tests/test_module_loader.py", "testing/tests/test_intent_pipeline.py"),
        "core/runtime/datetimeUtils.py": ("testing/tests/test_datetime_utils.py",),
        "core/runtime/logger.py": ("testing/tests/test_logger.py",),
        "core/runtime/moduleLoader.py": ("testing/tests/test_module_loader.py",),
        "core/runtime/observability": ("testing/tests/test_observability.py",),
        "core/runtime/runtimeContext.py": ("testing/tests/test_runtime_smoke.py",),
        "core/threading/events": ("testing/tests/test_events.py",),
        "core/threading/scheduler": ("testing/tests/test_threading_scheduler.py",),
        "core/threading/tasks": ("testing/tests/test_threading_scheduler.py",),
        "core/threading/threadingManager.py": ("testing/tests/test_threading_scheduler.py",),
        "core/tools": ("testing/tests/test_tool_system.py",),
        "core/voice/vad": ("testing/tests/test_vad.py",),
        "core/voice/wakeWord": ("testing/tests/test_wake_word.py",),
        "core/version.py": ("testing/tests/test_runtime_smoke.py",),
        "interface/android": ("testing/tests/interfaceTests/test_android_interface.py",),
        "interface/desktop/windows": ("testing/tests/test_desktop_overlay.py",),
        "interface/desktop/windows/email": (
            "testing/tests/modules/email/testEmailAccounts.py",
            "testing/tests/modules/email/testInboxReading.py",
            "testing/tests/modules/email/testEmailDrafts.py",
            "testing/tests/modules/email/testEmailScheduling.py",
            "testing/tests/modules/email/testEmailFiltering.py",
            "testing/tests/modules/email/testEmailNotifications.py",
            "testing/tests/modules/email/testEmailSafety.py",
            "testing/tests/modules/email/testEmailProviders.py",
        ),
        "interface/developerUI": ("testing/tests/test_developer_ui.py",),
        "interface/inputProcessing": ("testing/tests/test_voice.py",),
        "interface/model_status.py": ("testing/tests/interfaceTests/test_android_interface.py",),
        "interface/voice": ("testing/tests/test_voice.py",),
        "interface/voice/vad": ("testing/tests/test_vad.py",),
        "interface/voice/wakeWord": ("testing/tests/test_wake_word.py",),
        "interface/web": ("testing/tests/interfaceTests/test_web_interface.py",),
        "interface/windows": ("testing/tests/interfaceTests/test_windows_interface.py",),
        "modules/automation_composer": ("testing/tests/test_automation_composer.py",),
        "modules/base": ("testing/tests/test_module_loader.py",),
        "modules/personalSchedule": ("testing/tests/test_personal_schedule.py",),
        "modules/database": ("testing/tests/test_sqlite_database.py", "testing/tests/test_mysql_integration.py"),
        "modules/home_automation": ("testing/tests/test_home_automation.py",),
        "modules/logger": ("testing/tests/test_logger.py",),
        "modules/llm/contextAwareness": ("testing/tests/test_context_awareness.py",),
        "modules/llm/intent": ("testing/tests/test_intent_pipeline.py",),
        "modules/llm/manager": ("testing/tests/test_llm_handler.py",),
        "modules/llm/memory": ("testing/tests/test_memory_manager.py", "testing/tests/test_memory_retrieval.py"),
        "modules/llm/models": ("testing/tests/test_llm_handler.py", "testing/tests/test_intent_pipeline.py"),
        "modules/llm/prompts": ("testing/tests/test_prompt_builder.py",),
        "modules/llm/providers": ("testing/tests/test_llm_handler.py",),
        "modules/llm/testing": ("testing/tests/test_intent_pipeline.py",),
        "modules/llm/utils": ("testing/tests/test_prompt_builder.py", "testing/tests/test_llm_handler.py"),
        "modules/llm/conversationHistory.py": ("testing/tests/test_conversation_history.py",),
        "modules/llm/llmHandler.py": ("testing/tests/test_llm_handler.py",),
        "modules/llm/memoryManager.py": ("testing/tests/test_conversation_history.py",),
        "modules/email": (
            "testing/tests/modules/email/testEmailAccounts.py",
            "testing/tests/modules/email/testInboxReading.py",
            "testing/tests/modules/email/testEmailDrafts.py",
            "testing/tests/modules/email/testEmailScheduling.py",
            "testing/tests/modules/email/testEmailFiltering.py",
            "testing/tests/modules/email/testEmailNotifications.py",
            "testing/tests/modules/email/testEmailSafety.py",
            "testing/tests/modules/email/testEmailProviders.py",
        ),
        "modules/notifications": ("testing/tests/test_notifications.py",),
        "modules/smartHome": ("testing/tests/test_module_framework.py",),
        "modules/spotify": ("testing/tests/test_spotify_module.py", "testing/tests/test_module_framework.py"),
        "modules/weather": ("testing/tests/test_weather_module.py",),
        "modules/system": ("testing/tests/test_system.py",),
        "providers": ("testing/tests/test_architecture.py",),
        "providers/base": ("testing/tests/test_architecture.py",),
        "providers/embeddings": ("testing/tests/test_semantic_memory.py",),
        "providers/gemini": ("testing/tests/test_architecture.py",),
        "providers/ollama": ("testing/tests/test_architecture.py",),
        "providers/speech": ("testing/tests/test_architecture.py",),
        "scripts": (
            "testing/tests/interfaceTests/test_android_interface.py",
            "testing/tests/interfaceTests/test_web_interface.py",
            "testing/tests/interfaceTests/test_windows_interface.py",
            "testing/tests/test_developer_ui.py",
            "testing/tests/test_voice.py",
        ),
        "main.py": ("testing/tests/test_system.py", "testing/tests/test_runtime_smoke.py"),
        "runDeveloperUI.py": ("testing/tests/test_developer_ui.py",),
        "run_tests.py": ("testing/tests/test_build_compile.py",),
    }

    toolCoverage = {
        "automation.createDraft": "testing/tests/test_automation_composer.py",
        "automation.listPlans": "testing/tests/test_automation_composer.py",
        "automation.activate": "testing/tests/test_automation_composer.py",
        "automation.pause": "testing/tests/test_automation_composer.py",
        "automation.resume": "testing/tests/test_automation_composer.py",
        "automation.runNow": "testing/tests/test_automation_composer.py",
        "schedule.createItem": "testing/tests/test_personal_schedule.py",
        "schedule.createReminder": "testing/tests/test_personal_schedule.py",
        "schedule.createTask": "testing/tests/test_personal_schedule.py",
        "schedule.createTimer": "testing/tests/test_personal_schedule.py",
        "schedule.completeTimer": "testing/tests/test_personal_schedule.py",
        "schedule.getToday": "testing/tests/test_personal_schedule.py",
        "schedule.getUpcoming": "testing/tests/test_personal_schedule.py",
        "homeAutomation.toggleLight": "testing/tests/test_home_automation.py",
        "homeAutomation.getLightState": "testing/tests/test_home_automation.py",
        "homeAutomation.setLightBrightness": "testing/tests/test_home_automation.py",
        "lights.getState": "testing/tests/test_home_automation.py",
        "lights.setBrightness": "testing/tests/test_home_automation.py",
        "lights.setColor": "testing/tests/test_home_automation.py",
        "lights.turnOn": "testing/tests/test_home_automation.py",
        "lights.turnOff": "testing/tests/test_home_automation.py",
        "homeAutomation.setLightColor": "testing/tests/test_home_automation.py",
        "homeAutomation.startCameraStream": "testing/tests/test_home_automation.py",
        "homeAutomation.stopCameraStream": "testing/tests/test_home_automation.py",
        "homeAutomation.takeCameraSnapshot": "testing/tests/test_home_automation.py",
        "spotify.playTrack": "testing/tests/test_spotify_module.py",
        "spotify.pause": "testing/tests/test_spotify_module.py",
        "spotify.nextTrack": "testing/tests/test_spotify_module.py",
        "spotify.previousTrack": "testing/tests/test_spotify_module.py",
        "spotify.seek": "testing/tests/test_spotify_module.py",
        "spotify.setPlaybackSpeed": "testing/tests/test_spotify_module.py",
        "spotify.setVolume": "testing/tests/test_spotify_module.py",
        "spotify.searchTracks": "testing/tests/test_spotify_module.py",
        "spotify.searchPlaylists": "testing/tests/test_spotify_module.py",
        "spotify.playPlaylist": "testing/tests/test_spotify_module.py",
        "spotify.getNowPlaying": "testing/tests/test_spotify_module.py",
        "spotify.getPlaybackState": "testing/tests/test_spotify_module.py",
        "spotify.listDevices": "testing/tests/test_spotify_module.py",
        "spotify.transferPlayback": "testing/tests/test_spotify_module.py",
        "spotify.listPlaylists": "testing/tests/test_spotify_module.py",
        "email.listAccounts": "testing/tests/modules/email/testEmailAccounts.py",
        "email.connectAccount": "testing/tests/modules/email/testEmailAccounts.py",
        "email.setDefaultAccount": "testing/tests/modules/email/testEmailAccounts.py",
        "email.listInbox": "testing/tests/modules/email/testEmailAccounts.py",
        "email.readEmail": "testing/tests/modules/email/testEmailAccounts.py",
        "email.searchEmails": "testing/tests/modules/email/testEmailAccounts.py",
        "email.listDrafts": "testing/tests/modules/email/testEmailAccounts.py",
        "email.createDraft": "testing/tests/modules/email/testEmailAccounts.py",
        "email.updateDraft": "testing/tests/modules/email/testEmailAccounts.py",
        "email.sendEmail": "testing/tests/modules/email/testEmailAccounts.py",
        "email.scheduleEmail": "testing/tests/modules/email/testEmailAccounts.py",
        "email.listLabels": "testing/tests/modules/email/testEmailAccounts.py",
        "email.applyLabel": "testing/tests/modules/email/testEmailAccounts.py",
        "email.filterEmails": "testing/tests/modules/email/testEmailAccounts.py",
        "email.sortEmails": "testing/tests/modules/email/testEmailAccounts.py",
        "email.deleteEmail": "testing/tests/modules/email/testEmailAccounts.py",
        "email.archiveEmail": "testing/tests/modules/email/testEmailAccounts.py",
        "system.getTime": "testing/tests/test_system.py",
        "system.reload": "testing/tests/test_system.py",
        "weather.addLocation": "testing/tests/test_weather_module.py",
        "weather.addThreshold": "testing/tests/test_weather_module.py",
        "weather.getAlerts": "testing/tests/test_weather_module.py",
        "weather.getCurrent": "testing/tests/test_weather_module.py",
        "weather.getHourlyForecast": "testing/tests/test_weather_module.py",
        "weather.getIndoorTemperature": "testing/tests/test_weather_module.py",
        "weather.getWeeklyForecast": "testing/tests/test_weather_module.py",
        "weather.listLocations": "testing/tests/test_weather_module.py",
    }

    def test_every_source_file_belongs_to_a_tested_feature_area(self):
        """Every production Python file should be owned by a named test area."""

        uncovered = []
        featurePrefixes = tuple(sorted(self.testedFeatureAreas, key=len, reverse=True))
        for path in self._productionPythonFiles():
            rel = self._relative(path)
            if rel.endswith("__init__.py"):
                continue
            if not any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in featurePrefixes):
                uncovered.append(rel)

        self.assertEqual(uncovered, [])

    def test_every_tested_feature_area_has_real_tests(self):
        """Feature ownership entries should point to real unittest files."""

        missing = []
        empty = []
        for feature, tests in self.testedFeatureAreas.items():
            for testPath in tests:
                path = self.root / testPath
                if not path.exists():
                    missing.append(f"{feature}: {testPath}")
                    continue
                if "def test_" not in path.read_text(encoding="utf-8", errors="ignore"):
                    empty.append(f"{feature}: {testPath}")

        self.assertEqual(missing, [])
        self.assertEqual(empty, [])

    def test_every_registered_runtime_tool_has_dedicated_test_coverage(self):
        """Every Tool(...) registration should be named in its dedicated test file."""

        registeredTools = self._registeredToolNames()
        missingMappings = sorted(set(registeredTools) - set(self.toolCoverage))
        staleMappings = sorted(set(self.toolCoverage) - set(registeredTools))
        missingMentions = []

        for toolName, testPath in self.toolCoverage.items():
            path = self.root / testPath
            text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            if toolName not in text:
                missingMentions.append(f"{toolName}: {testPath}")

        self.assertEqual(missingMappings, [])
        self.assertEqual(staleMappings, [])
        self.assertEqual(missingMentions, [])

    def test_every_production_python_file_compiles(self):
        """Production source files should at least have syntax/import-time coverage."""

        failures = []
        for path in self._productionPythonFiles():
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as error:
                failures.append(f"{self._relative(path)}: {error}")

        self.assertEqual(failures, [])

    def test_run_tests_all_matches_unittest_discovery(self):
        """The full-suite runner should execute the same tests as unittest discovery."""

        loader = unittest.TestLoader()
        discovered = loader.discover("testing/tests")
        configured = run_tests.buildSuite("all")

        self.assertEqual(self._testIds(configured), self._testIds(discovered))

    def _productionPythonFiles(self) -> list[Path]:
        """Return non-test Python files owned by Aura source roots."""

        files = []
        for path in self.root.rglob("*.py"):
            rel = path.relative_to(self.root)
            if any(part in self.excludedParts for part in rel.parts):
                continue
            if rel.parts[0] == "testing":
                continue
            if rel.parts[0] in self.sourceRoots or rel.name in {"main.py", "runDeveloperUI.py", "run_tests.py"}:
                files.append(path)
        return sorted(files)

    def _registeredToolNames(self) -> list[str]:
        """Extract registered Tool names from production source files."""

        names = []
        for path in self._productionPythonFiles():
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not self._isToolCall(node):
                    continue
                for keyword in node.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        names.append(str(keyword.value.value))
        return sorted(names)

    @staticmethod
    def _isToolCall(node: ast.Call) -> bool:
        """Return whether an AST call appears to instantiate core.tools.Tool."""

        if isinstance(node.func, ast.Name):
            return node.func.id == "Tool"
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "Tool"
        return False

    def _relative(self, path: Path) -> str:
        """Return a stable slash-separated path relative to the repository root."""

        return path.relative_to(self.root).as_posix()

    @classmethod
    def _testIds(cls, suite: unittest.TestSuite) -> list[str]:
        """Flatten a unittest suite into sorted test IDs."""

        ids = []
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                ids.extend(cls._testIds(item))
            else:
                ids.append(item.id())
        return sorted(ids)


if __name__ == "__main__":
    unittest.main()
