"""Tests for Aura's Windows desktop interface package.

These tests validate the new Windows runtime/bootstrap and GUI entry
points while isolating external dependencies (Tk, MySQL, LLM, scheduler).
The goal is to keep interface tests deterministic and fast in CI.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tests.support.fakes import make_context
from core.threading.events.events import Event


class _FakeLogger:
    """Minimal logger stub that matches Aura's `getChild` logging usage."""

    def getChild(self, _name):
        """Return this logger instance for chained child logger calls."""

        return self

    def info(self, _message):
        """Accept info logs without side effects."""

    def error(self, _message):
        """Accept error logs without side effects."""

    def warning(self, _message):
        """Accept warning logs without side effects."""


class _FakeConfigLoader:
    """Config loader stub for runtime bootstrap tests."""

    def __init__(self, _context):
        """Initialize static config values required by runtime services."""

        self._data = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "pass",
                "name": "aura",
            },
            "llm": {
                "endpoint": "http://localhost:11434/api/generate",
                "model": "llama3.1:8b",
            },
        }

    def get(self, key, default=None):
        """Return a config value using dot-path resolution."""

        value = self._data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def require(self, key):
        """Return a required config value or raise when missing."""

        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value


class _FailingConfigLoader:
    """Config loader stub that simulates invalid/corrupt config files."""

    def __init__(self, _context):
        """Raise an error immediately to emulate config load failure."""

        raise ValueError("invalid config format")


class _MissingConfigLoader:
    """Config loader stub that omits required keys for recovery-path tests."""

    def __init__(self, _context):
        """Initialize incomplete config data with missing required entries."""

        self._data = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "name": "aura",
                "user": "root",
                # database.password intentionally missing
            },
            "llm": {
                # llm.endpoint intentionally missing
                "model": "llama3.1:8b",
            },
        }

    def get(self, key, default=None):
        """Return a config value using dot-path resolution."""

        value = self._data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def require(self, key):
        """Return a required config value or raise when missing."""

        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value


class _PlaceholderConfigLoader:
    """Config loader stub that uses template placeholder values."""

    def __init__(self, _context):
        """Initialize config values that should trigger recovery prompts."""

        self._data = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "name": "change_me",
                "user": "change_me",
                "password": "change_me",
            },
            "llm": {
                "endpoint": "http://localhost:11434/api/generate",
                "model": "llama3.1:8b",
            },
        }

    def get(self, key, default=None):
        """Return a config value using dot-path resolution."""

        value = self._data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def require(self, key):
        """Return a required config value or raise when missing."""

        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value


class _FakeThreadingManager:
    """No-op threading manager used during bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility with production manager."""


class _FakeEventManager:
    """No-op event manager used during bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility with production manager."""

        self.listeners = {}

    def subscribe(self, event_name, callback):
        """Record event subscriptions made by the Windows UI."""

        self.listeners.setdefault(event_name, []).append(callback)

    def emit(self, event):
        """Dispatch fake events to subscribed callbacks."""

        for callback in self.listeners.get(event.name, []):
            callback(event)


class _FakeTaskManager:
    """No-op task manager used during bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility with production manager."""


class _FakeScheduler:
    """Scheduler stub that tracks lifecycle calls."""

    def __init__(self, _context):
        """Initialize scheduler call-tracking flags."""

        self.started = False
        self.stopped = False
        self.schedules = {}

    def start(self):
        """Track scheduler startup calls."""

        self.started = True

    def stop(self):
        """Track scheduler shutdown calls."""

        self.stopped = True

    def addSchedule(self, schedule):
        """Store registered schedules by name."""

        self.schedules[schedule.name] = schedule

    def getSchedule(self, name):
        """Return one registered schedule by name."""

        return self.schedules.get(name)


class _FakeDatabase:
    """Database stub that tracks connect/initialize/close lifecycle calls."""

    def __init__(self, _context):
        """Initialize lifecycle flags for database operations."""

        self.connected = False
        self.initialized = False
        self.closed = False

    def connect(self):
        """Track connect operations."""

        self.connected = True

    def initialize(self):
        """Track initialize operations."""

        self.initialized = True

    def close(self):
        """Track close operations."""

        self.closed = True


class _FailingDatabase:
    """Database stub that simulates failed connection setup."""

    def __init__(self, _context):
        """Initialize failing database constructor."""

    def connect(self):
        """Raise a connection error during startup."""

        raise RuntimeError("database offline")


class _FakeMemoryManager:
    """No-op memory manager stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FakeConversationHistory:
    """No-op conversation history stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FakeLLMHandler:
    """No-op LLM handler stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FailingLLMHandler:
    """LLM handler stub that simulates initialization failure."""

    def __init__(self, _context):
        """Raise an error immediately to emulate LLM startup failure."""

        raise RuntimeError("llm init failed")


class _FakeInterpreter:
    """No-op interpreter stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FakeIntentRouter:
    """No-op intent router stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FakeInputManager:
    """No-op input manager stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FakeOutputManager:
    """No-op output manager stub for bootstrap tests."""

    def __init__(self, _context):
        """Store constructor compatibility."""


class _FakeModuleLoader:
    """Module loader stub that records whether loading was triggered."""

    def __init__(self, _context):
        """Initialize load tracking state."""

        self.loaded = False

    def loadModules(self):
        """Track module loading calls."""

        self.loaded = True


class _NoOpModuleLoader:
    """Module loader stub that simulates dynamic module discovery failure."""

    def __init__(self, _context):
        """Initialize loader compatibility without loading anything."""

    def loadModules(self):
        """Skip all module registration work."""


class _FakeRoot:
    """Tk root replacement used to test GUI logic without opening windows."""

    def __init__(self):
        """Initialize root state used by AuraWindowsApp tests."""

        self.exists = True
        self.protocol_callback = None
        self.after_calls = []

    def title(self, _value):
        """Accept title assignment."""

    def geometry(self, _value):
        """Accept geometry assignment."""

    def minsize(self, _width, _height):
        """Accept minsize assignment."""

    def protocol(self, _name, callback):
        """Store the window protocol callback."""

        self.protocol_callback = callback

    def configure(self, **_kwargs):
        """Accept root style configuration."""

    def iconbitmap(self, **_kwargs):
        """Accept window icon assignment."""

    def after(self, _delay, callback):
        """Track scheduled callbacks without executing them."""

        self.after_calls.append(callback)

    def mainloop(self):
        """No-op mainloop for test mode."""

    def destroy(self):
        """Mark the root as destroyed."""

        self.exists = False

    def winfo_exists(self):
        """Report whether this fake root is still alive."""

        return self.exists


class _FakeFrame:
    """Frame widget replacement with no-op layout behavior."""

    def __init__(self, _parent, **_kwargs):
        """Initialize frame placeholder."""
        self.is_packed = False
        self.is_placed = False

    def pack(self, **_kwargs):
        """Accept pack layout calls."""
        self.is_packed = True

    def pack_propagate(self, _flag):
        """Accept propagation configuration calls."""

    def pack_forget(self):
        """Accept pack removal calls."""
        self.is_packed = False

    def place(self, **_kwargs):
        """Accept absolute placement calls."""
        self.is_placed = True

    def place_forget(self):
        """Accept placement removal calls."""
        self.is_placed = False

    def lift(self):
        """Accept z-order adjustment calls."""


class _FakeEntry:
    """Entry widget replacement that stores and returns plain text values."""

    def __init__(self, _parent, **_kwargs):
        """Initialize input state and bind storage."""

        self.value = ""
        self.state = "normal"
        self.bindings = {}

    def pack(self, **_kwargs):
        """Accept pack layout calls."""

    def bind(self, event_name, callback):
        """Store key-binding callbacks."""

        self.bindings[event_name] = callback

    def get(self):
        """Return current text value."""

        return self.value

    def delete(self, _start, _end):
        """Clear current text value."""

        self.value = ""

    def configure(self, **kwargs):
        """Track widget configuration updates."""

        if "state" in kwargs:
            self.state = kwargs["state"]

    def focus_set(self):
        """Accept focus assignment."""


class _FakeButton:
    """Button widget replacement that tracks state/text changes."""

    def __init__(self, _parent, text, command, **_kwargs):
        """Initialize button with default text and bound command."""

        self.text = text
        self.command = command
        self.state = "normal"
        self.bg = _kwargs.get("bg")
        self.fg = _kwargs.get("fg")

    def pack(self, **_kwargs):
        """Accept pack layout calls."""

    def configure(self, **kwargs):
        """Track button state and text updates."""

        if "state" in kwargs:
            self.state = kwargs["state"]
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "bg" in kwargs:
            self.bg = kwargs["bg"]
        if "fg" in kwargs:
            self.fg = kwargs["fg"]


class _FakeScrolledText:
    """Scrolled text replacement that appends messages to an internal buffer."""

    def __init__(self, _parent, wrap, state, **_kwargs):
        """Initialize transcript storage and widget state."""

        self.wrap = wrap
        self.state = state
        self.content = ""

    def pack(self, **_kwargs):
        """Accept pack layout calls."""

    def configure(self, **kwargs):
        """Track state updates."""

        if "state" in kwargs:
            self.state = kwargs["state"]

    def insert(self, _location, text, *_tags):
        """Append text to transcript buffer."""

        self.content += text

    def delete(self, _start, _end):
        """Clear the transcript buffer."""

        self.content = ""

    def see(self, _location):
        """Accept auto-scroll requests."""

    def tag_configure(self, _tag_name, **_kwargs):
        """Accept tag styling calls."""


class _FakeLabel:
    """Label widget replacement with no-op styling and layout behavior."""

    def __init__(self, _parent, **_kwargs):
        """Initialize label placeholder."""

    def pack(self, **_kwargs):
        """Accept pack layout calls."""


class _ImmediateThread:
    """Thread replacement that executes target immediately in test process."""

    def __init__(self, target, args=(), daemon=True):
        """Store thread target metadata."""

        self._target = target
        self._args = args
        self.daemon = daemon

    def start(self):
        """Run target synchronously for deterministic tests."""

        self._target(*self._args)


class WindowsRuntimeBootstrapTests(unittest.TestCase):
    """Validate context creation and lifecycle behavior for Windows bootstrap."""

    def test_ensure_config_file_exists_creates_default_template(self):
        """Ensure missing config file is generated with default template values."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            ensureConfigFileExists,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            created = ensureConfigFileExists(str(config_path))

            self.assertTrue(created)
            self.assertTrue(config_path.exists())
            content = config_path.read_text(encoding="utf-8")
            self.assertIn("llm:", content)
            self.assertIn("database:", content)
            self.assertIn("threading:", content)

    def test_ensure_config_file_exists_does_not_overwrite_existing_file(self):
        """Ensure auto-generation does not replace an existing config file."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            ensureConfigFileExists,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            original_content = "llm:\n  model: test-model\n"
            config_path.write_text(original_content, encoding="utf-8")

            created = ensureConfigFileExists(str(config_path))

            self.assertFalse(created)
            self.assertEqual(config_path.read_text(encoding="utf-8"), original_content)

    def test_ensure_config_file_exists_migrates_legacy_config_location(self):
        """Ensure legacy `config/config.yml` is migrated into root-level `config.yml`."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            ensureConfigFileExists,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            previous_cwd = Path.cwd()
            try:
                temp_root = Path(temp_dir)
                legacy_path = temp_root / "config" / "config.yml"
                legacy_path.parent.mkdir(parents=True, exist_ok=True)
                legacy_content = "database:\n  name: migrated_db\n"
                legacy_path.write_text(legacy_content, encoding="utf-8")

                os.chdir(temp_root)

                created = ensureConfigFileExists("config.yml")

                self.assertTrue(created)
                self.assertTrue((temp_root / "config.yml").exists())
                self.assertEqual(
                    (temp_root / "config.yml").read_text(encoding="utf-8"),
                    legacy_content,
                )
            finally:
                os.chdir(previous_cwd)

    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ModuleLoader", _FakeModuleLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.OutputManager", _FakeOutputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.InputManager", _FakeInputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.IntentRouter", _FakeIntentRouter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Interpreter", _FakeInterpreter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.LLMHandler", _FakeLLMHandler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConversationHistory", _FakeConversationHistory)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MemoryManager", _FakeMemoryManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MySQLDatabase", _FakeDatabase)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Scheduler", _FakeScheduler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.TaskManager", _FakeTaskManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.EventManager", _FakeEventManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ThreadingManager", _FakeThreadingManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConfigLoader", _FakeConfigLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.AuraLogger", return_value=_FakeLogger())
    def test_create_context_startup_and_shutdown(self, _mock_logger):
        """Ensure bootstrap creates context and runs scheduler/database lifecycle."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            createRuntimeContext,
            shutdown,
            startup,
        )

        context = createRuntimeContext()

        self.assertIsNotNone(context.config)
        self.assertIsNotNone(context.database)
        self.assertTrue(context.database.connected)
        self.assertTrue(context.database.initialized)
        self.assertFalse(context.should_exit)

        startup(context)
        self.assertTrue(context.scheduler.started)

        shutdown(context)
        self.assertTrue(context.scheduler.stopped)
        self.assertTrue(context.database.closed)

    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ModuleLoader", _FakeModuleLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.OutputManager", _FakeOutputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.InputManager", _FakeInputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.IntentRouter", _FakeIntentRouter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Interpreter", _FakeInterpreter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.LLMHandler", _FailingLLMHandler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConversationHistory", _FakeConversationHistory)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MemoryManager", _FakeMemoryManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MySQLDatabase", _FailingDatabase)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Scheduler", _FakeScheduler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.TaskManager", _FakeTaskManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.EventManager", _FakeEventManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ThreadingManager", _FakeThreadingManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConfigLoader", _FailingConfigLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.AuraLogger", return_value=_FakeLogger())
    def test_create_context_uses_fallbacks_when_config_and_db_fail(self, _mock_logger):
        """Ensure runtime boot continues with fallback components on startup failures."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            DegradedLLMHandler,
            InMemoryConversationHistory,
            InMemoryMemoryManager,
            UnavailableDatabase,
            createRuntimeContext,
        )

        context = createRuntimeContext()

        self.assertIsInstance(context.database, UnavailableDatabase)
        self.assertIsInstance(context.memoryManager, InMemoryMemoryManager)
        self.assertIsInstance(context.conversationHistory, InMemoryConversationHistory)
        self.assertIsInstance(context.llm, DegradedLLMHandler)
        self.assertGreaterEqual(len(context.bootstrapWarnings), 1)
        self.assertIn("LLM is currently unavailable", context.llm.generateResponse("hello"))

    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConfigLoader", _MissingConfigLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.AuraLogger", return_value=_FakeLogger())
    def test_create_context_exposes_missing_config_keys_for_recovery(self, _mock_logger):
        """Ensure bootstrap returns missing keys for interactive recovery flow."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            createRuntimeContext,
        )

        context = createRuntimeContext()

        self.assertIn("database.password", context.missingConfigKeys)
        self.assertIn("llm.endpoint", context.missingConfigKeys)
        self.assertFalse(context.should_exit)
        self.assertEqual(len(context.missingConfigKeys), len(set(context.missingConfigKeys)))

    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConfigLoader", _PlaceholderConfigLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.AuraLogger", return_value=_FakeLogger())
    def test_create_context_treats_template_placeholders_as_missing(self, _mock_logger):
        """Ensure template placeholder values trigger interactive recovery instead of DB startup."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            createRuntimeContext,
        )

        context = createRuntimeContext()

        self.assertIn("database.name", context.missingConfigKeys)
        self.assertIn("database.user", context.missingConfigKeys)
        self.assertIn("database.password", context.missingConfigKeys)

    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.registerRemindersModule")
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.registerCommandsModule")
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ModuleLoader", _NoOpModuleLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.OutputManager", _FakeOutputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.InputManager", _FakeInputManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.IntentRouter", _FakeIntentRouter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Interpreter", _FakeInterpreter)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.LLMHandler", _FakeLLMHandler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConversationHistory", _FakeConversationHistory)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MemoryManager", _FakeMemoryManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.MySQLDatabase", _FakeDatabase)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.Scheduler", _FakeScheduler)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.TaskManager", _FakeTaskManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.EventManager", _FakeEventManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ThreadingManager", _FakeThreadingManager)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.ConfigLoader", _FakeConfigLoader)
    @patch("core.interface.desktopInterface.windows.windowsRuntimeBootstrap.AuraLogger", return_value=_FakeLogger())
    def test_create_context_registers_critical_modules_when_loader_skips_them(
        self,
        _mock_logger,
        mock_register_commands_module,
        mock_register_reminders_module,
    ):
        """Ensure Windows bootstrap directly registers command/reminder modules when needed."""

        from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
            createRuntimeContext,
        )

        context = createRuntimeContext()

        mock_register_commands_module.assert_called_once_with(context)
        mock_register_reminders_module.assert_called_once_with(context)


class RunAuraWindowsEntrypointTests(unittest.TestCase):
    """Validate entrypoint lifecycle orchestration for the Windows runtime."""

    @patch("core.interface.desktopInterface.windows.runAuraWindows.showStandaloneErrorPopup")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.shutdown")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.startup")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.createRuntimeContext")
    def test_main_still_shuts_down_when_gui_raises(
        self,
        mock_create_runtime_context,
        mock_startup,
        mock_shutdown,
        mock_error_popup,
    ):
        """Ensure shutdown and error popup execute when GUI runtime raises an exception."""

        from core.interface.desktopInterface.windows.runAuraWindows import main

        fake_context = SimpleNamespace()
        mock_create_runtime_context.return_value = fake_context

        with patch(
            "core.interface.desktopInterface.windows.runAuraWindows.AuraWindowsApp"
        ) as mock_app_class:
            mock_app = mock_app_class.return_value
            mock_app.run.side_effect = RuntimeError("boom")
            main()

        mock_startup.assert_called_once_with(fake_context)
        mock_shutdown.assert_called_once_with(fake_context)
        mock_error_popup.assert_called_once()

    @patch("core.interface.desktopInterface.windows.runAuraWindows.shutdown")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.startup")
    @patch("core.interface.desktopInterface.windows.runAuraWindows._applyConfigOverridesToEnv")
    @patch("core.interface.desktopInterface.windows.runAuraWindows._promptForMissingConfigValues")
    @patch("core.interface.desktopInterface.windows.runAuraWindows.createRuntimeContext")
    def test_main_prompts_for_missing_config_then_retries_startup(
        self,
        mock_create_runtime_context,
        mock_prompt_for_values,
        mock_apply_overrides,
        mock_startup,
        mock_shutdown,
    ):
        """Ensure missing config prompts are collected and startup retries once values are provided."""

        from core.interface.desktopInterface.windows.runAuraWindows import main

        first_context = SimpleNamespace(missingConfigKeys=["database.host", "llm.endpoint"])
        second_context = SimpleNamespace(missingConfigKeys=[])

        mock_create_runtime_context.side_effect = [first_context, second_context]
        mock_prompt_for_values.return_value = {
            "database.host": "127.0.0.1",
            "llm.endpoint": "http://localhost:11434/api/generate",
        }

        with patch(
            "core.interface.desktopInterface.windows.runAuraWindows.AuraWindowsApp"
        ) as mock_app_class:
            mock_app = mock_app_class.return_value
            main()

        self.assertEqual(mock_create_runtime_context.call_count, 2)
        mock_prompt_for_values.assert_called_once_with(first_context.missingConfigKeys)
        mock_apply_overrides.assert_called_once()
        mock_startup.assert_called_once_with(second_context)
        mock_app.run.assert_called_once()
        mock_shutdown.assert_called_once_with(second_context)

    @patch("core.interface.desktopInterface.windows.runAuraWindows.startup")
    @patch("core.interface.desktopInterface.windows.runAuraWindows._promptForMissingConfigValues", return_value=None)
    @patch("core.interface.desktopInterface.windows.runAuraWindows.createRuntimeContext")
    def test_main_exits_when_config_prompt_is_canceled(
        self,
        mock_create_runtime_context,
        _mock_prompt_for_values,
        mock_startup,
    ):
        """Ensure startup exits cleanly when user cancels config recovery prompts."""

        from core.interface.desktopInterface.windows.runAuraWindows import main

        mock_create_runtime_context.return_value = SimpleNamespace(
            missingConfigKeys=["database.host"]
        )

        main()
        mock_startup.assert_not_called()


class AuraWindowsAppTests(unittest.TestCase):
    """Validate UI command submission flow and close behavior with fake widgets."""

    def _build_app(self, context):
        """Create AuraWindowsApp with patched Tkinter and threading primitives."""

        from core.interface.desktopInterface.windows.auraWindowsApp import AuraWindowsApp

        patchers = [
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Tk", _FakeRoot),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Frame", _FakeFrame),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Label", _FakeLabel),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Entry", _FakeEntry),
            patch("core.interface.desktopInterface.windows.auraWindowsApp.Button", _FakeButton),
            patch(
                "core.interface.desktopInterface.windows.auraWindowsApp.ScrolledText",
                _FakeScrolledText,
            ),
            patch(
                "core.interface.desktopInterface.windows.auraWindowsApp.Thread",
                _ImmediateThread,
            ),
        ]

        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        return AuraWindowsApp(context)

    def test_submit_processes_input_and_appends_response(self):
        """Ensure submit sends text through InputManager and renders response."""

        context = make_context(
            extra={
                "inputManager": SimpleNamespace(
                    process=lambda text: f"processed:{text}",
                ),
                "logger": _FakeLogger(),
            }
        )

        app = self._build_app(context)
        app.inputEntry.value = "/help"

        app._onSubmit()
        app._pollPendingResponses()

        self.assertIn("You: /help", app.transcript.content)
        self.assertIn("Aura: processed:/help", app.transcript.content)
        self.assertFalse(app.isBusy)
        self.assertTrue(len(app.root.after_calls) >= 1)

    def test_show_reminders_page_refreshes_list_and_marks_page_active(self):
        """Ensure the reminders page loads data and becomes the active visible page."""

        reminders = SimpleNamespace(
            listReminders=lambda: [
                {
                    "id": 2,
                    "title": "Pay rent",
                    "remind_at": "2026-03-30 09:00",
                    "created_at": "2026-03-23 18:00",
                }
            ]
        )
        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "reminders": reminders,
                "logger": _FakeLogger(),
            }
        )

        app = self._build_app(context)
        app._showRemindersPage()

        self.assertEqual(app.activePage, "reminders")
        self.assertTrue(app.remindersPage.is_packed)
        self.assertFalse(app.chatPage.is_packed)
        self.assertIn("Pay rent", app.remindersTranscript.content)

    def test_add_reminder_calls_backend_and_refreshes_page(self):
        """Ensure reminder creation uses the existing reminders manager API."""

        created = []

        reminders = SimpleNamespace(
            createReminder=lambda title, remind_at=None: created.append((title, remind_at)),
            listReminders=lambda: [],
        )
        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "reminders": reminders,
                "logger": _FakeLogger(),
            }
        )

        app = self._build_app(context)
        app.reminderTitleEntry.value = "Buy groceries"
        app.reminderWhenEntry.value = "2026-03-24 17:00"

        app._addReminder()

        self.assertEqual(created, [("Buy groceries", "2026-03-24 17:00")])
        self.assertEqual(app.reminderTitleEntry.value, "")
        self.assertEqual(app.reminderWhenEntry.value, "")

    def test_delete_reminder_calls_backend_and_refreshes_page(self):
        """Ensure reminder deletion uses the existing reminders manager API."""

        deleted = []

        reminders = SimpleNamespace(
            deleteReminder=lambda reminder_id: deleted.append(reminder_id),
            listReminders=lambda: [],
        )
        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "reminders": reminders,
                "logger": _FakeLogger(),
            }
        )

        app = self._build_app(context)
        app.deleteReminderEntry.value = "7"

        app._deleteReminder()

        self.assertEqual(deleted, [7])
        self.assertEqual(app.deleteReminderEntry.value, "")

    def test_shutdown_signal_schedules_close(self):
        """Ensure app schedules window close when runtime requests shutdown."""

        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "logger": _FakeLogger(),
            }
        )
        context.should_exit = True

        app = self._build_app(context)
        app._checkForShutdownSignal()

        self.assertIn(app._closeWindow, app.root.after_calls)

    def test_submit_processing_error_shows_error_popup(self):
        """Ensure runtime processing failures trigger the error popup hook."""

        def _raise_error(_text):
            raise RuntimeError("processing failed")

        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=_raise_error),
                "logger": _FakeLogger(),
            }
        )

        app = self._build_app(context)
        app.inputEntry.value = "/help"
        app._showErrorPopup = MagicMock()

        app._onSubmit()
        app._pollPendingResponses()

        app._showErrorPopup.assert_called_once()

    def test_reminder_event_shows_popup_and_transcript_entry(self):
        """Ensure emitted reminder events surface in the Windows app."""

        event_manager = _FakeEventManager(None)
        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "eventManager": event_manager,
                "logger": _FakeLogger(),
            }
        )

        app = self._build_app(context)
        app._showReminderPopup = MagicMock()

        event_manager.emit(
            Event(
                "reminder_triggered",
                {"title": "Stretch", "remind_at": "2026-03-23 17:28:00"},
            )
        )
        app._pollPendingResponses()

        self.assertIn("Reminder: Stretch (2026-03-23 17:28:00)", app.transcript.content)
        app._showReminderPopup.assert_called_once()

    @patch("core.interface.desktopInterface.windows.auraWindowsApp.messagebox.askyesno", return_value=False)
    def test_busy_close_cancel_keeps_window_open(self, _mock_prompt):
        """Ensure close prompt can cancel window close while request is active."""

        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "logger": _FakeLogger(),
            }
        )
        app = self._build_app(context)
        app.isBusy = True

        app._onWindowClose()
        self.assertTrue(app.root.winfo_exists())

    @patch("core.interface.desktopInterface.windows.auraWindowsApp.messagebox.askyesno", return_value=True)
    def test_busy_close_confirm_closes_window(self, _mock_prompt):
        """Ensure close prompt confirmation closes the window while request is active."""

        context = make_context(
            extra={
                "inputManager": SimpleNamespace(process=lambda _text: "ok"),
                "logger": _FakeLogger(),
            }
        )
        app = self._build_app(context)
        app.isBusy = True

        app._onWindowClose()
        self.assertFalse(app.root.winfo_exists())


if __name__ == "__main__":
    unittest.main()
