"""Tests for Aura's centralized logger behavior."""

import tempfile
import time
import unittest
from pathlib import Path

from core.runtime.logger import AuraLogger
from modules.logger.llmLogger import LLMLogger
from modules.logger.logger import Logger


class LoggerTests(unittest.TestCase):
    """Validate latest.log lifecycle and isolated LLM logging."""

    def test_logger_creates_latest_log_and_writes_messages(self):
        """Ensure logger creates latest.log and writes formatted output."""

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logger = AuraLogger(name="AuraLoggerTestCreate", logs_dir=str(logs_dir))
            logger.info("test message")

            self.assertTrue(logs_dir.exists())
            self.assertTrue(logger.logFilePath.exists())
            content = logger.logFilePath.read_text(encoding="utf-8")
            self.assertIn("SESSION_START:", content)
            self.assertIn("[INFO] [AuraLoggerTestCreate] test message", content)
            self.assertIn("test message", content)
            logger.close()

    def test_logger_rotates_existing_latest_log_on_startup(self):
        """Ensure a previous latest.log is renamed and a fresh latest.log starts."""

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"

            first_logger = AuraLogger(name="AuraLoggerTestRotate", logs_dir=str(logs_dir))
            first_logger.info("first session")
            time.sleep(0.01)
            second_logger = AuraLogger(name="AuraLoggerTestRotate", logs_dir=str(logs_dir))
            second_logger.info("second session")

            latest_path = logs_dir / "latest.log"
            rotated = [path for path in logs_dir.glob("*.log") if path.name != "latest.log"]
            self.assertTrue(latest_path.exists())
            self.assertTrue(rotated)
            self.assertIn("second session", latest_path.read_text(encoding="utf-8"))
            first_logger.close()
            second_logger.close()

    def test_llm_logger_writes_to_isolated_latest_log(self):
        """Ensure LLM traces are written separately from runtime logs."""

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            llm_dir = logs_dir / "llm"
            manager_logger = Logger("Test", config={
                "logging": {
                    "logPath": str(logs_dir),
                    "llmLogPath": str(llm_dir),
                    "loggingEnabled": True,
                    "consoleLoggingEnabled": False,
                    "fileLoggingEnabled": True,
                    "debugLoggingEnabled": True,
                }
            })
            llm_logger = LLMLogger(logManager=manager_logger.logManager)
            llm_logger.logInteraction(
                provider="Gemini 2.5 Flash",
                systemPrompt="system",
                memoryContext="memory",
                userMessage="hello",
                rawResponse="world",
                latency=1.42,
            )

            standard_content = (logs_dir / "latest.log").read_text(encoding="utf-8")
            llm_content = (llm_dir / "latest.log").read_text(encoding="utf-8")
            self.assertNotIn("SYSTEM PROMPT:", standard_content)
            self.assertIn("PROVIDER: Gemini 2.5 Flash", llm_content)
            self.assertIn("LATENCY:\n1.42s", llm_content)


if __name__ == "__main__":
    unittest.main()
