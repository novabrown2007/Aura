"""Automated tests for `test_system_commands` behavior and regression coverage."""

import unittest

from modules.commands.commandHandler import CommandHandler
from modules.commands.systemCommands.systemCommandHandler import SystemCommandHandler
from modules.commands.systemCommands.shutdownCommand import ShutdownCommand
from tests.support.fakes import make_context


class SystemCommandsTests(unittest.TestCase):
    """Test cases covering `SystemCommandsTests` behavior and expected command/runtime outcomes."""
    def setUp(self):
        """Prepare the test fixture state before each test case executes."""
        self.context = make_context()
        self.context.commandHandler = CommandHandler(self.context)
        self.context.systemCommandHandler = SystemCommandHandler(self.context)
        ShutdownCommand(self.context)

    def test_shutdown_command_sets_exit_flag(self):
        """Validate that shutdown command sets exit flag behaves as expected."""
        self.assertFalse(self.context.should_exit)

        result = self.context.commandHandler.handle("/system shutdown")

        self.assertEqual(result, "Shutting down Aura...")
        self.assertTrue(self.context.should_exit)

    def test_unknown_system_command_returns_invalid_message(self):
        """Validate that unknown system command returns invalid message behaves as expected."""
        result = self.context.commandHandler.handle("/system does-not-exist")
        self.assertIn('is not a valid command', result)


if __name__ == "__main__":
    unittest.main()

