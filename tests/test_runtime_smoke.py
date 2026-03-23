"""Smoke tests that validate command bootstrap and core command execution flow."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.runtime.moduleLoader import ModuleLoader
from tests.support.fakes import InMemoryDatabase, make_context


class RuntimeSmokeTests(unittest.TestCase):
    """Ensures runtime command bootstrapping works through ModuleLoader."""

    def setUp(self):
        """Build a lightweight runtime context with required dependencies for commands."""

        self.context = make_context(database=InMemoryDatabase())
        self.context.memoryManager = SimpleNamespace(
            getMemory=lambda: {},
            get=lambda key: None,
            setMemory=lambda key, value, importance=1: None,
            delete=lambda key: None,
            clear=lambda: None,
        )
        self.context.conversationHistory = SimpleNamespace(
            getRecentMessages=lambda limit=15: [],
            clear=lambda: None,
            logMessage=lambda author, content: None,
        )
        self.context.llm = SimpleNamespace(
            endpoint="http://localhost:11434/api/generate",
            model="llama3.1:8b",
        )
        self.context.modules = {"commands": object()}
        self.context.threader = SimpleNamespace(
            listThreads=lambda: [],
            stopThread=lambda name: None,
        )
        self.context.taskManager = SimpleNamespace(
            tasks={},
            getTask=lambda name: None,
            completedTasks=lambda: [],
        )
        self.context.scheduler = SimpleNamespace(running=False)

    @patch("modules.commands.debugCommands.llmDebugCommand.requests.post")
    def test_runtime_smoke_command_flow(self, mock_post):
        """Boot commands via ModuleLoader and execute representative core commands."""

        mock_post.return_value = SimpleNamespace(
            status_code=200,
            json=lambda: {"response": "pong"},
        )

        loader = ModuleLoader(self.context)
        loader.loadModules()

        command_handler = self.context.commandHandler
        self.assertIsNotNone(command_handler)

        help_output = command_handler.handle("/help")
        status_output = command_handler.handle("/status")
        config_validate_output = command_handler.handle("/config validate")
        db_ping_output = command_handler.handle("/debug database ping")

        self.assertIn("/help", help_output)
        self.assertIn("database_connected: True", status_output)
        self.assertEqual(config_validate_output, "Configuration validation passed.")
        self.assertEqual(db_ping_output, "Database ping: ok.")

