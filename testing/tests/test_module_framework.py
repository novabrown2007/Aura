"""Tests for Aura's formal module framework."""

from __future__ import annotations

import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from core.modules import (
    ModuleManager,
    ModuleMetadata,
    ModulePermissions,
    ModuleState,
    ModuleSubscription,
    ModuleValidator,
)
from core.runtime.runtimeContext import RuntimeContext
from modules.personalSchedule import PersonalScheduleModule
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

    def test_module_contract_models_round_trip(self):
        """The core module contract models should serialize cleanly."""

        metadata = ModuleMetadata(
            name="contract",
            version="2.1.0",
            author="Aura",
            description="Test module",
            dependencies=("alpha",),
            requiredPermissions=("spotify.control",),
            capabilities=("music.playback",),
            website="https://example.invalid/module",
        )
        intent = importlib.import_module("core.modules.base.moduleIntent").ModuleIntent(
            name="contract.intent",
            description="Contract intent",
            arguments={"track": "string"},
            target="runContract",
            requiredArguments=("track",),
            validationRequirements=("track",),
        )
        action = importlib.import_module("core.modules.base.moduleAction").ModuleAction(
            name="contract.action",
            description="Contract action",
            method="runContract",
            parameters={"track": "string"},
            requiredParameters=("track",),
            validationRequirements=("track",),
            permissions=("spotify.control",),
            capabilities=("music.playback",),
        )
        subscription = ModuleSubscription(
            eventName="contract.event",
            handler="handleContractEvent",
            description="Contract subscription",
            target="handleContractEvent",
        )

        self.assertEqual(metadata.asDict()["requiredPermissions"], ["spotify.control"])
        self.assertEqual(metadata.asDict()["permissions"], ["spotify.control"])
        self.assertEqual(metadata.asDict()["website"], "https://example.invalid/module")
        self.assertEqual(intent.asDict()["validationRequirements"], ["track"])
        self.assertEqual(action.asDict()["validationRequirements"], ["track"])
        self.assertEqual(subscription.asDict()["handler"], "handleContractEvent")

    def test_module_validator_rejects_invalid_package(self):
        """The module validator should reject packages that do not expose the contract."""

        validator = ModuleValidator(self._makeContext())
        report = validator.validatePackage(object())

        self.assertFalse(report.valid)
        self.assertGreaterEqual(len(report.errors), 1)

    def test_module_manager_registers_subscription_handlers(self):
        """Module event subscriptions should register and bind to declared handlers."""

        self._writePlugin(
            "gamma",
            """
            from core.modules.base import AuraModule, ModuleMetadata, ModuleSubscription

            MODULE_METADATA = ModuleMetadata(name="gamma")

            def createModule(context=None):
                return Gamma()

            class Gamma(AuraModule):
                metadata = MODULE_METADATA

                def __init__(self):
                    super().__init__()
                    self.received = []

                def getSubscriptions(self):
                    return [ModuleSubscription(eventName="gamma.event", handler="handleGammaEvent")]

                def handleGammaEvent(self, event):
                    self.received.append(event)
                    return event
            """,
        )

        context = self._makeContext()
        manager = ModuleManager(context, packageName=self.package_name)
        manager.loadModules()

        self.assertIn("gamma.event", context.eventManager.subscriptions)
        handler = context.eventManager.subscriptions["gamma.event"][0]
        self.assertTrue(callable(handler))

        payload = {"name": "gamma.event", "data": {"value": 1}}
        handler(payload)
        gamma = manager.loadedModules["gamma"]
        self.assertEqual(gamma.received, [payload])

    def test_example_modules_expose_standard_contract(self):
        """The initial example modules should expose metadata, actions, and intents."""

        for moduleClass in (PersonalScheduleModule, WeatherModule, SpotifyModule, SmartHomeModule):
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
