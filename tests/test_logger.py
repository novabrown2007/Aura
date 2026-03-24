"""Tests for Aura's file-backed logger behavior."""

import tempfile
import time
import unittest
from pathlib import Path

from core.runtime.logger import AuraLogger


class LoggerTests(unittest.TestCase):
    """Validate log directory creation and per-run file generation."""

    def test_logger_creates_logs_directory_and_writes_messages(self):
        """Ensure logger creates a logs folder and writes output to a run log file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logger = AuraLogger(name="AuraLoggerTestCreate", logs_dir=str(logs_dir))
            logger.info("test message")

            self.assertTrue(logs_dir.exists())
            self.assertTrue(logger.logFilePath.exists())
            content = logger.logFilePath.read_text(encoding="utf-8")
            self.assertIn("logger.py has been initialized.", content)
            self.assertIn("test message", content)
            logger.close()

    def test_logger_creates_a_new_file_for_each_startup(self):
        """Ensure separate logger startups create separate run log files."""

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"

            first_logger = AuraLogger(name="AuraLoggerTestRotate", logs_dir=str(logs_dir))
            first_path = first_logger.logFilePath
            time.sleep(0.01)
            second_logger = AuraLogger(name="AuraLoggerTestRotate", logs_dir=str(logs_dir))
            second_path = second_logger.logFilePath

            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.exists())
            self.assertTrue(second_path.exists())
            first_logger.close()
            second_logger.close()


if __name__ == "__main__":
    unittest.main()
