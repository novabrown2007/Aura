"""Automated tests for `test_command_registry` behavior and regression coverage."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.runtime.moduleLoader import ModuleLoader
from modules.commands.commandRegistry import CommandRegistry
from tests.support.fakes import InMemoryDatabase, make_context


class StubMemoryManager:
    """Testing utility class used to simulate `StubMemoryManager` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubMemoryManager` with required dependencies and internal state."""
        self.data = {}

    def setMemory(self, key, value, importance=1):
        """Update component state for `setMemory` using provided input values."""
        self.data[key] = value

    def get(self, key):
        """Return `get` data from the component's current state."""
        return self.data.get(key)

    def getMemory(self):
        """Return `getMemory` data from the component's current state."""
        return dict(self.data)

    def delete(self, key):
        """Implement `delete` as part of this component's public/internal behavior."""
        self.data.pop(key, None)

    def clear(self):
        """Implement `clear` as part of this component's public/internal behavior."""
        self.data.clear()


class StubConversationHistory:
    """Testing utility class used to simulate `StubConversationHistory` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubConversationHistory` with required dependencies and internal state."""
        self.messages = []

    def logMessage(self, author, content):
        """Implement `logMessage` as part of this component's public/internal behavior."""
        self.messages.append((author, content))

    def getRecentMessages(self, limit=15):
        """Return `getRecentMessages` data from the component's current state."""
        return self.messages[-limit:]

    def clear(self):
        """Implement `clear` as part of this component's public/internal behavior."""
        self.messages.clear()


class StubTask:
    """Testing utility class used to simulate `StubTask` dependencies and behavior."""
    def __init__(self, name, completed=False, error=None):
        """Initialize `StubTask` with required dependencies and internal state."""
        self.name = name
        self.completed = completed
        self.error = error


class StubTaskManager:
    """Testing utility class used to simulate `StubTaskManager` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubTaskManager` with required dependencies and internal state."""
        self.tasks = {"example": StubTask("example", completed=False)}

    def getTask(self, name):
        """Return `getTask` data from the component's current state."""
        return self.tasks.get(name)

    def completedTasks(self):
        """Implement `completedTasks` as part of this component's public/internal behavior."""
        return [task for task in self.tasks.values() if task.completed]


class StubThreader:
    """Testing utility class used to simulate `StubThreader` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubThreader` with required dependencies and internal state."""
        self.stopped = []
        self.threads = {"task_example": object()}

    def listThreads(self):
        """Return a list representation for `listThreads` from current runtime state."""
        return list(self.threads.keys())

    def stopThread(self, name):
        """Implement `stopThread` as part of this component's public/internal behavior."""
        self.stopped.append(name)


class CommandRegistryTests(unittest.TestCase):
    """Test cases covering `CommandRegistryTests` behavior and expected command/runtime outcomes."""
    def setUp(self):
        """Prepare the test fixture state before each test case executes."""
        self.context = make_context(
            database=InMemoryDatabase(),
            extra={
                "memoryManager": StubMemoryManager(),
                "conversationHistory": StubConversationHistory(),
                "llm": SimpleNamespace(
                    endpoint="http://localhost:11434/api/generate",
                    model="llama3.1:8b",
                ),
                "modules": {"weather": object(), "commands": object()},
                "taskManager": StubTaskManager(),
                "threader": StubThreader(),
                "scheduler": SimpleNamespace(running=False),
            },
        )
        CommandRegistry(self.context)

    def test_registry_initializes_handlers(self):
        """Validate that registry initializes handlers behaves as expected."""
        self.assertIsNotNone(self.context.commandHandler)
        self.assertIsNotNone(self.context.debugCommandHandler)
        self.assertIsNotNone(self.context.configCommandHandler)
        self.assertIsNotNone(self.context.historyCommandHandler)
        self.assertIsNotNone(self.context.memoryCommandHandler)
        self.assertIsNotNone(self.context.systemCommandHandler)

    def test_help_lists_registered_commands(self):
        """Validate that help lists registered commands behaves as expected."""
        output = self.context.commandHandler.handle("/help")
        self.assertIn("/help", output)
        self.assertIn("/status", output)
        self.assertIn("/version", output)
        self.assertIn("/debug memory", output)
        self.assertIn("/debug database", output)
        self.assertIn("/debug llm", output)
        self.assertIn("/config reload", output)
        self.assertIn("/memory set", output)
        self.assertIn("/history show", output)
        self.assertIn("/system shutdown", output)

    def test_config_reload_command_executes(self):
        """Validate that config reload command executes behaves as expected."""
        result = self.context.commandHandler.handle("/config reload")
        self.assertEqual(result, "Configuration reloaded.")
        self.assertEqual(self.context.config.reload_calls, 1)

    def test_config_get_set_validate_commands(self):
        """Validate that config get set validate commands behaves as expected."""
        set_result = self.context.commandHandler.handle("/config set llm.model test-model")
        get_result = self.context.commandHandler.handle("/config get llm.model")
        validate_result = self.context.commandHandler.handle("/config validate")

        self.assertIn("Config updated", set_result)
        self.assertEqual(get_result, "llm.model = test-model")
        self.assertEqual(validate_result, "Configuration validation passed.")

    def test_memory_and_history_commands(self):
        """Validate that memory and history commands behaves as expected."""
        self.context.commandHandler.handle('/memory set name "Nova"')
        get_result = self.context.commandHandler.handle("/memory get name")
        list_result = self.context.commandHandler.handle("/memory list")
        search_result = self.context.commandHandler.handle("/memory search nov")

        self.assertEqual(get_result, "name = Nova")
        self.assertIn("name = Nova", list_result)
        self.assertIn("name = Nova", search_result)

        self.context.conversationHistory.logMessage("user", "hello")
        show_result = self.context.commandHandler.handle("/history show 5")
        clear_result = self.context.commandHandler.handle("/history clear")

        self.assertIn("user: hello", show_result)
        self.assertEqual(clear_result, "Conversation history cleared.")

    def test_system_commands_modules_tasks_and_restart(self):
        """Validate that system commands modules tasks and restart behaves as expected."""
        modules_result = self.context.commandHandler.handle("/system modules list")
        tasks_result = self.context.commandHandler.handle("/system tasks list")
        cancel_result = self.context.commandHandler.handle("/system tasks cancel example")
        restart_result = self.context.commandHandler.handle("/system restart")

        self.assertIn("weather", modules_result)
        self.assertIn("example [running]", tasks_result)
        self.assertEqual(cancel_result, 'Task "example" cancel requested.')
        self.assertEqual(restart_result, "Restart requested. Shutting down Aura...")
        self.assertTrue(self.context.should_exit)
        self.assertTrue(getattr(self.context, "should_restart", False))
        self.assertIn("task_example", self.context.threader.stopped)

    @patch("modules.commands.debugCommands.llmDebugCommand.requests.post")
    def test_debug_and_root_commands(self, mock_post):
        """Validate that debug and root commands behaves as expected."""
        mock_post.return_value = SimpleNamespace(status_code=200, json=lambda: {"response": "pong"})

        llm_ping = self.context.commandHandler.handle("/debug llm ping")
        db_ping = self.context.commandHandler.handle("/debug database ping")
        db_schema = self.context.commandHandler.handle("/debug database schema")
        runtime = self.context.commandHandler.handle("/debug runtime")
        status = self.context.commandHandler.handle("/status")
        version = self.context.commandHandler.handle("/version")

        self.assertIn("LLM ping: ok", llm_ping)
        self.assertEqual(db_ping, "Database ping: ok.")
        self.assertIn("DATABASE TABLES", db_schema)
        self.assertIn("threads:", runtime)
        self.assertIn("database_connected: True", status)
        self.assertIn("Aura version:", version)

    def test_module_loader_bootstraps_command_system(self):
        """Validate that module loader bootstraps command system behaves as expected."""
        context = make_context(database=InMemoryDatabase())
        loader = ModuleLoader(context)
        loader.loadModules()

        self.assertIsNotNone(context.commandHandler)
        self.assertIsNotNone(context.debugCommandHandler)
        self.assertIsNotNone(context.configCommandHandler)
        self.assertIsNotNone(context.historyCommandHandler)
        self.assertIsNotNone(context.memoryCommandHandler)
        self.assertIsNotNone(context.systemCommandHandler)

    def test_command_execution_is_persisted_to_command_logs(self):
        """Validate that command executions are persisted to database-backed command logs."""

        self.context.commandHandler.handle("/status")
        self.context.commandHandler.handle("/not-a-real-command")

        logs = self.context.database._command_logs
        self.assertGreaterEqual(len(logs), 2)

        last_two = logs[-2:]
        self.assertEqual(last_two[0]["command_text"], "/status")
        self.assertEqual(last_two[0]["status"], "success")
        self.assertEqual(last_two[1]["command_text"], "/not-a-real-command")
        self.assertEqual(last_two[1]["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
