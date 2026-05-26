"""Smoke tests for Aura's backend runtime."""

import threading
import time
import unittest
from types import SimpleNamespace

from core.engine import Engine
from core.router.interpreter import Interpreter
from core.runtime.datetimeUtils import DateTimeUtils
from testing.tests.support.fakes import InMemoryDatabase, make_context


class RuntimeSmokeTests(unittest.TestCase):
    """Ensure the backend runtime boots and idles until shutdown."""

    def setUp(self):
        """Build a lightweight runtime context for headless processing testing.tests."""

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
        self.context.engine = Engine(self.context)

    def test_engine_run_waits_headlessly_until_shutdown(self):
        """Ensure the engine loop stays idle until the runtime is told to stop."""

        worker = threading.Thread(target=self.context.engine.run, kwargs={"poll_interval": 0.01})
        worker.start()
        time.sleep(0.05)
        self.assertTrue(worker.is_alive())

        self.context.should_exit = True
        worker.join(timeout=1.0)

        self.assertFalse(worker.is_alive())

    def test_context_exposes_datetime_utility_as_dt_util(self):
        """Ensure the shared datetime utility is available on the runtime context."""

        self.assertIs(self.context.dtUtil, DateTimeUtils)
        self.assertEqual(
            self.context.dtUtil.toPreferredDate("2026-03-24"),
            "24/03/2026",
        )


if __name__ == "__main__":
    unittest.main()
