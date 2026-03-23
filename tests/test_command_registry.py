import unittest

from core.runtime.moduleLoader import ModuleLoader
from modules.commands.commandRegistry import CommandRegistry
from tests.support.fakes import InMemoryDatabase, make_context


class CommandRegistryTests(unittest.TestCase):
    def setUp(self):
        self.context = make_context(database=InMemoryDatabase())
        CommandRegistry(self.context)

    def test_registry_initializes_handlers(self):
        self.assertIsNotNone(self.context.commandHandler)
        self.assertIsNotNone(self.context.debugCommandHandler)
        self.assertIsNotNone(self.context.configCommandHandler)
        self.assertIsNotNone(self.context.systemCommandHandler)

    def test_help_lists_registered_commands(self):
        output = self.context.commandHandler.handle("/help")
        self.assertIn("/help", output)
        self.assertIn("/debug memory", output)
        self.assertIn("/debug database", output)
        self.assertIn("/config reload", output)
        self.assertIn("/system shutdown", output)

    def test_config_reload_command_executes(self):
        result = self.context.commandHandler.handle("/config reload")
        self.assertEqual(result, "Configuration reloaded.")
        self.assertEqual(self.context.config.reload_calls, 1)

    def test_module_loader_bootstraps_command_system(self):
        context = make_context(database=InMemoryDatabase())
        loader = ModuleLoader(context)
        loader.loadModules()

        self.assertIsNotNone(context.commandHandler)
        self.assertIsNotNone(context.debugCommandHandler)
        self.assertIsNotNone(context.configCommandHandler)
        self.assertIsNotNone(context.systemCommandHandler)


if __name__ == "__main__":
    unittest.main()
