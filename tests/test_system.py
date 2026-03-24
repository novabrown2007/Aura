"""Tests for Aura's system lifecycle module."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main
from modules.system.reload import Reload
from modules.system.restart import Restart
from modules.system.shutdown import Shutdown
from modules.system.system import System
from tests.support.fakes import make_context


class _RecordingConfig:
    """Config stub that records reload calls and exposes dict output."""

    def __init__(self):
        """Initialize config state."""

        self.reload_calls = 0
        self.data = {"database": {"host": "localhost"}}

    def reload(self):
        """Record reload invocation."""

        self.reload_calls += 1

    def asDict(self):
        """Return the current config dictionary."""

        return dict(self.data)


class _RecordingLogger:
    """Logger stub with child logger compatibility for lifecycle tests."""

    def __init__(self):
        """Initialize captured log state."""

        self.children = []
        self.closed = False

    def getChild(self, name):
        """Return self as a child logger."""

        self.children.append(name)
        return self

    def info(self, _message):
        """Accept info log calls."""

        return None

    def close(self):
        """Record logger shutdown."""

        self.closed = True


class SystemModuleTests(unittest.TestCase):
    """Validate shutdown, restart, and reload lifecycle behaviors."""

    def test_shutdown_sets_exit_without_restart(self):
        """Shutdown should stop the runtime without requesting a new cycle."""

        context = make_context(extra={"logger": _RecordingLogger()})

        result = Shutdown(context).execute()

        self.assertTrue(result)
        self.assertTrue(context.should_exit)
        self.assertFalse(context.restart_requested)

    def test_restart_sets_exit_and_restart_flags(self):
        """Restart should stop the current runtime and request a new one."""

        context = make_context(extra={"logger": _RecordingLogger()})

        result = Restart(context).execute()

        self.assertTrue(result)
        self.assertTrue(context.should_exit)
        self.assertTrue(context.restart_requested)

    def test_reload_refreshes_config_and_returns_updated_values(self):
        """Reload should refresh the config object and return the current dict."""

        config = _RecordingConfig()
        context = make_context(extra={"logger": _RecordingLogger(), "config": config})

        result = Reload(context).execute()

        self.assertEqual(config.reload_calls, 1)
        self.assertEqual(result, {"database": {"host": "localhost"}})

    def test_system_facade_exposes_all_lifecycle_actions(self):
        """The system facade should delegate to the three lifecycle actions."""

        config = _RecordingConfig()
        context = make_context(extra={"logger": _RecordingLogger(), "config": config})
        system = System(context)

        self.assertTrue(system.shutdown())
        self.assertTrue(context.should_exit)

        context.should_exit = False
        self.assertTrue(system.restart())
        self.assertTrue(context.restart_requested)

        result = system.reload()
        self.assertEqual(result, {"database": {"host": "localhost"}})


class MainLifecycleTests(unittest.TestCase):
    """Validate restart looping in the top-level application entrypoint."""

    def test_main_rebuilds_context_when_restart_is_requested(self):
        """Main should bootstrap a fresh runtime context after a restart request."""

        first_context = SimpleNamespace(
            engine=SimpleNamespace(run=lambda: setattr(first_context, "restart_requested", True) or setattr(first_context, "should_exit", True)),
            logger=_RecordingLogger(),
            restart_requested=False,
            should_exit=False,
        )
        second_context = SimpleNamespace(
            engine=SimpleNamespace(run=lambda: setattr(second_context, "should_exit", True)),
            logger=_RecordingLogger(),
            restart_requested=False,
            should_exit=False,
        )

        with patch.object(main, "buildRuntimeContext", side_effect=[first_context, second_context]) as build_context:
            with patch.object(main, "startup") as startup_runtime, patch.object(main, "shutdown") as shutdown_runtime:
                main.main()

        self.assertEqual(build_context.call_count, 2)
        self.assertEqual(startup_runtime.call_count, 2)
        self.assertEqual(shutdown_runtime.call_count, 2)
        self.assertTrue(first_context.logger.closed)
        self.assertTrue(second_context.logger.closed)


if __name__ == "__main__":
    unittest.main()
