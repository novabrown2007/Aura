"""Smoke tests for Aura's headless runtime API."""

import threading
import time
import unittest
from types import SimpleNamespace

from core.engine.engine import Engine
from core.interface.io.inputManager import InputManager
from core.interface.io.outputManager import OutputManager
from core.router.intentRouter import IntentRouter
from core.router.interpreter import Interpreter
from tests.support.fakes import InMemoryDatabase, make_context


class RuntimeSmokeTests(unittest.TestCase):
    """Ensure the runtime boots without a CLI and processes API requests."""

    def setUp(self):
        """Build a lightweight runtime context for headless processing tests."""

        self.context = make_context(database=InMemoryDatabase())
        self.context.memoryManager = SimpleNamespace(
            getMemory=lambda: {},
            get=lambda key: None,
            setMemory=lambda key, value, importance=1: None,
            delete=lambda key: None,
            clear=lambda: None,
            learnFromMessage=lambda message: None,
        )
        self.context.conversationHistory = SimpleNamespace(
            getRecentMessages=lambda limit=15: [],
            clear=lambda: None,
            logMessage=lambda author, content: None,
        )
        self.context.llm = SimpleNamespace(
            generateResponse=lambda text: f"llm:{text}",
        )
        self.context.interpreter = Interpreter(self.context)
        self.context.intentRouter = IntentRouter(self.context)
        self.context.outputManager = OutputManager(self.context)
        self.context.inputManager = InputManager(self.context)
        self.context.engine = Engine(self.context)

    def test_engine_handles_input_through_headless_api(self):
        """Ensure engine request handling returns a packet and publishes output."""

        packet = self.context.engine.handleInput("Hello there", source="test")

        self.assertEqual(packet["source"], "test")
        self.assertEqual(packet["input"], "Hello there")
        self.assertEqual(packet["intent"], "llm")
        self.assertEqual(packet["response"], "llm:Hello there")
        self.assertEqual(
            self.context.outputManager.getLastMessage()["response"],
            "llm:Hello there",
        )

    def test_engine_run_waits_headlessly_until_shutdown(self):
        """Ensure the engine loop stays idle until the runtime is told to stop."""

        worker = threading.Thread(target=self.context.engine.run, kwargs={"poll_interval": 0.01})
        worker.start()
        time.sleep(0.05)
        self.assertTrue(worker.is_alive())

        self.context.should_exit = True
        worker.join(timeout=1.0)

        self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
