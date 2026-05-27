"""Tests for Aura's dynamic module loader and plugin contract."""

from __future__ import annotations

import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from core.router.intent import Intent
from core.runtime.moduleLoader import ModuleLoader
from core.runtime.runtimeContext import RuntimeContext
from modules.base import AuraModule
from modules.calendar import Calendar
from modules.database.mysql.mysqlDatabase import MySQLDatabase
from modules.database.sqlite.sqliteDatabase import SQLiteDatabase
from modules.home_automation import HomeAutomation
from modules.llm.conversationHistory import ConversationHistory
from modules.llm.llmHandler import LLMHandler
from modules.llm.memoryManager import MemoryManager
from modules.notifications import Notifications
from modules.reminders import Reminders
from modules.system import System


class DictConfig:
    """Small config adapter for module loader testing.tests."""

    def __init__(self, values=None):
        """Store config values."""

        self.values = values or {}

    def get(self, key, default=None):
        """Return dot-path config values."""

        value = self.values
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value


class ModuleLoaderTests(unittest.TestCase):
    """Test dynamic plugin loading behavior."""

    def setUp(self):
        """Create a temporary plugin package."""

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
        """Remove temporary modules from import state."""

        sys.path.remove(str(self.root))
        for module_name in list(sys.modules):
            if module_name == self.package_name or module_name.startswith(f"{self.package_name}."):
                sys.modules.pop(module_name, None)
        sys.dont_write_bytecode = self.previous_dont_write_bytecode
        self.tempdir.cleanup()

    def test_loads_modules_in_dependency_order(self):
        """Dependencies should initialize before dependents."""

        self._writePlugin(
            "alpha",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="alpha")
            def createModule(context=None):
                return Alpha()
            class Alpha(AuraModule):
                metadata = MODULE_METADATA
                def initialize(self, context):
                    super().initialize(context)
                    context.order.append("alpha")
            """,
        )
        self._writePlugin(
            "beta",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="beta", dependencies=("alpha",))
            def createModule(context=None):
                return Beta()
            class Beta(AuraModule):
                metadata = MODULE_METADATA
                def initialize(self, context):
                    super().initialize(context)
                    context.order.append("beta")
            """,
        )
        context = self._makeContext()
        context.order = []

        ModuleLoader(context, package_name=self.package_name).loadModules()

        self.assertEqual(context.order, ["alpha", "beta"])

    def test_existing_modules_follow_aura_module_contract(self):
        """Existing backend modules should inherit the standard contract."""

        module_classes = (
            Calendar,
            HomeAutomation,
            ConversationHistory,
            LLMHandler,
            MemoryManager,
            MySQLDatabase,
            Notifications,
            Reminders,
            SQLiteDatabase,
            System,
        )

        for module_class in module_classes:
            with self.subTest(module=module_class.__name__):
                module = module_class()
                self.assertIsInstance(module, AuraModule)
                self.assertTrue(module.metadata.name)
                self.assertIsInstance(module.getIntents(), list)
                self.assertTrue(hasattr(module, "handleIntent"))

    def test_disabled_module_is_not_loaded(self):
        """Config can disable modules."""

        self._writePlugin(
            "weather",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="weather")
            def createModule(context=None):
                return Weather()
            class Weather(AuraModule):
                metadata = MODULE_METADATA
                def initialize(self, context):
                    super().initialize(context)
                    context.loaded_weather = True
            """,
        )
        context = self._makeContext({"modules": {"weather": {"enabled": False}}})

        loader = ModuleLoader(context, package_name=self.package_name)
        loader.loadModules()

        self.assertNotIn("weather", loader.loadedModules)
        self.assertFalse(hasattr(context, "loaded_weather"))

    def test_user_facing_module_status_strings_control_loading(self):
        """Config can use enabled/disabled strings for module status."""

        self._writePlugin(
            "weather",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="weather")
            def createModule(context=None):
                return Weather()
            class Weather(AuraModule):
                metadata = MODULE_METADATA
                def initialize(self, context):
                    super().initialize(context)
                    context.loaded_weather = True
            """,
        )
        context = self._makeContext({"modules": {"weather": "disabled"}})

        loader = ModuleLoader(context, package_name=self.package_name)
        loader.loadModules()

        self.assertNotIn("weather", loader.loadedModules)
        self.assertFalse(hasattr(context, "loaded_weather"))

    def test_user_facing_snake_case_module_aliases_control_loading(self):
        """Config can use package-style snake_case names for camelCase modules."""

        self._writePlugin(
            "home_automation",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="homeAutomation")
            def createModule(context=None):
                return HomeAutomation()
            class HomeAutomation(AuraModule):
                metadata = MODULE_METADATA
                def initialize(self, context):
                    super().initialize(context)
                    context.loaded_home_automation = True
            """,
        )
        context = self._makeContext({"modules": {"home_automation": "disabled"}})

        loader = ModuleLoader(context, package_name=self.package_name)
        loader.loadModules()

        self.assertNotIn("homeAutomation", loader.loadedModules)
        self.assertFalse(hasattr(context, "loaded_home_automation"))

    def test_metadata_permissions_and_capabilities_are_available(self):
        """Loader exposes plugin metadata, permissions, and capabilities."""

        self._writePlugin(
            "spotify",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(
                name="spotify",
                permissions=("network:http",),
                capabilities=("music-control",),
            )
            def createModule(context=None):
                return Spotify()
            class Spotify(AuraModule):
                metadata = MODULE_METADATA
            """,
        )
        context = self._makeContext()

        loader = ModuleLoader(context, package_name=self.package_name)
        loader.loadModules()

        self.assertEqual(loader.getMetadata("spotify").permissions, ("network:http",))
        self.assertEqual(loader.listPermissions()["spotify"], ["network:http"])
        self.assertEqual(loader.listCapabilities()["spotify"], ["music-control"])

    def test_module_intents_route_through_standard_contract(self):
        """AuraModule handles intents through the standard methods."""

        self._writePlugin(
            "weather",
            """
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="weather")
            def createModule(context=None):
                return Weather()
            class Weather(AuraModule):
                metadata = MODULE_METADATA
                def getIntents(self):
                    return ["weather.current"]
                def handleIntent(self, intent):
                    return "sunny"
            """,
        )
        context = self._makeContext()

        loader = ModuleLoader(context, package_name=self.package_name)
        loader.loadModules()
        module = loader.loadedModules["weather"]

        self.assertTrue(module.canHandle(Intent("weather.current", "weather")))
        self.assertEqual(module.handle(Intent("weather.current", "weather")), "sunny")

    def test_hot_reload_reinitializes_module(self):
        """Hot reload should shutdown the old instance and initialize a new one."""

        self._writeReloadablePlugin("version one")
        context = self._makeContext()
        loader = ModuleLoader(context, package_name=self.package_name)
        loader.loadModules()
        self.assertEqual(context.reload_value, "version one")

        self._writeReloadablePlugin("version two")
        importlib.invalidate_caches()
        loader.reloadModule("reloadable")

        self.assertEqual(context.reload_value, "version two")
        self.assertTrue(context.reload_shutdown_called)

    def _writeReloadablePlugin(self, value):
        self._writePlugin(
            "reloadable",
            f"""
            from modules.base import AuraModule, ModuleMetadata
            MODULE_METADATA = ModuleMetadata(name="reloadable")
            def createModule(context=None):
                return Reloadable()
            class Reloadable(AuraModule):
                metadata = MODULE_METADATA
                def initialize(self, context):
                    super().initialize(context)
                    context.reload_value = {value!r}
                def shutdown(self):
                    self.context.reload_shutdown_called = True
            """,
        )

    def _writePlugin(self, name, source):
        package_dir = self.package_dir / name
        package_dir.mkdir(exist_ok=True)
        (package_dir / "__init__.py").write_text(
            textwrap.dedent(source).strip() + "\n",
            encoding="utf-8",
        )
        importlib.invalidate_caches()

    @staticmethod
    def _makeContext(config_values=None):
        context = RuntimeContext()
        context.config = DictConfig(config_values)
        context.logger = None
        context.reload_shutdown_called = False
        return context


if __name__ == "__main__":
    unittest.main()
