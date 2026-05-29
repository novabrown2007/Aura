"""Tests for Aura's formal module framework."""

from __future__ import annotations

import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from core.modules import ModuleManager, ModuleMetadata, ModulePermissions, ModuleState
from core.runtime.runtimeContext import RuntimeContext
from modules.smartHome import SmartHomeModule
from modules.spotify import SpotifyModule
from modules.weather import WeatherModule


class DictConfig:
    """Small config adapter for module framework testing."""

    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        value = self.values
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value


class FakeEventBus:
    """Minimal event bus used to validate module lifecycle emissions."""

    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def emit(self, name, data=None):
        event = {"name": name, "data": dict(data or {})}
        self.events.append(event)
        return event

    def subscribe(self, name, handler):
        self.subscriptions.setdefault(name, []).append(handler)

    def unsubscribe(self, name, handler):
        handlers = self.subscriptions.get(name, [])
        if handler in handlers:
            handlers.remove(handler)


class ModuleFrameworkTests(unittest.TestCase):
    """Validate the formal module framework and example modules."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.package_name = "fake_aura_modules"
        self.package_dir = self.root / self.package_name
        self.package_dir.mkdir()
        (self.package_dir / "__init__.py").write_text("", encoding="utf-8")
        self.previous_dont_write_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.root))
        importlib.invalidate_caches()

    def tearDown(self):
        sys.path.remove(str(self.root))
        for module_name in list(sys.modules):
            if module_name == self.package_name or module_name.startswith(f"{self.package_name}."):
                sys.modules.pop(module_name, None)
        sys.dont_write_bytecode = self.previous_dont_write_bytecode
        self.tempdir.cleanup()

    def test_module_manager_discovers_registers_and_tracks_lifecycle(self):
        """The module manager should discover, load, and track module state."""

        self._writePlugin(
            "alpha",
            """
            from core.modules.base import AuraModule, ModuleAction, ModuleIntent, ModuleMetadata

            MODULE_METADATA = ModuleMetadata(
                name="alpha",
                version="1.0.0",
                author="Aura",
                capabilities=("alpha.capability",),
            )

            def createModule(context=None):
                return Alpha()

            class Alpha(AuraModule):
                metadata = MODULE_METADATA

                def getIntents(self):
                    return [ModuleIntent(name="alpha.intent", target="doAlpha")]

                def getActions(self):
                    return [ModuleAction(name="alpha.action", method="doAlpha")]

                def doAlpha(self):
                    return {"ok": True}
            """,
        )
        self._writePlugin(
            "beta",
            """
            from core.modules.base import AuraModule, ModuleMetadata

            MODULE_METADATA = ModuleMetadata(name="beta", dependencies=("alpha",))

            def createModule(context=None):
                return Beta()

            class Beta(AuraModule):
                metadata = MODULE_METADATA
            """,
        )

        context = self._makeContext()
        manager = ModuleManager(context, packageName=self.package_name)
        manager.loadModules()

        self.assertIn("alpha", manager.loadedModules)
        self.assertIn("beta", manager.loadedModules)
        self.assertEqual(manager.registry.entries["alpha"].state, ModuleState.RUNNING)
        self.assertEqual(manager.registry.entries["beta"].state, ModuleState.RUNNING)
        self.assertEqual(manager.registry.entries["alpha"].metadata.capabilities, ("alpha.capability",))
        self.assertEqual(manager.registry.entries["alpha"].intents[0].name, "alpha.intent")
        self.assertEqual(manager.registry.entries["alpha"].actions[0].name, "alpha.action")
        self.assertIn("module.loaded", [event["name"] for event in context.eventManager.events])
        self.assertIn("module.started", [event["name"] for event in context.eventManager.events])

        manager.pauseModule("alpha", manager.loadedModules["alpha"])
        self.assertEqual(manager.registry.entries["alpha"].state, ModuleState.PAUSED)
        manager.resumeModule("alpha", manager.loadedModules["alpha"])
        self.assertEqual(manager.registry.entries["alpha"].state, ModuleState.RUNNING)
        manager.shutdownModules()
        self.assertEqual(manager.registry.entries["alpha"].state, ModuleState.UNLOADED)
        self.assertEqual(manager.registry.entries["beta"].state, ModuleState.UNLOADED)

    def test_module_manager_compatibility_wrapper_is_preserved(self):
        """The legacy runtime loader should remain a ModuleManager alias."""

        from core.runtime.moduleLoader import ModuleLoader

        self.assertTrue(issubclass(ModuleLoader, ModuleManager))

    def test_example_modules_expose_standard_contract(self):
        """The initial example modules should expose metadata, actions, and intents."""

        for moduleClass in (WeatherModule, SpotifyModule, SmartHomeModule):
            with self.subTest(module=moduleClass.__name__):
                module = moduleClass()
                self.assertIsInstance(module.metadata, ModuleMetadata)
                self.assertTrue(module.metadata.name)
                self.assertGreaterEqual(len(module.getIntents()), 1)
                self.assertGreaterEqual(len(module.getActions()), 1)
                self.assertIsInstance(module.getPermissions(), ModulePermissions)

        weather = WeatherModule()
        self.assertEqual(weather.getCurrentWeather("Toronto")["location"], "Toronto")
        spotify = SpotifyModule()
        self.assertTrue(spotify.playSong(track="Example", artist="Artist")["isPlaying"])
        smartHome = SmartHomeModule()
        self.assertTrue(smartHome.turnLightOn("bedroom")["isOn"])

    def _writePlugin(self, name, source):
        package_dir = self.package_dir / name
        package_dir.mkdir(exist_ok=True)
        (package_dir / "__init__.py").write_text(
            textwrap.dedent(source).strip() + "\n",
            encoding="utf-8",
        )
        importlib.invalidate_caches()

    def _makeContext(self, config_values=None):
        context = RuntimeContext()
        context.config = DictConfig(config_values)
        context.logger = None
        context.eventManager = FakeEventBus()
        context.modules = {}
        return context


if __name__ == "__main__":
    unittest.main()
