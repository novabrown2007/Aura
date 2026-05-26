"""Tests for SQLite database adapter behavior."""

import tempfile
import threading
import unittest
from pathlib import Path

from modules.database.sqlite.sqliteDatabase import SQLiteDatabase


class SQLiteDatabaseTests(unittest.TestCase):
    """Validate SQLite fallback adapter behavior."""

    def test_connection_can_be_used_across_ui_worker_threads(self):
        """The UI can create SQLite on one thread and query it on another."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database = SQLiteDatabase(database_path=str(Path(temp_dir) / "aura.sqlite3"))
            database.connect()
            database.execute("CREATE TABLE IF NOT EXISTS thread_test (value TEXT)")
            database.execute("INSERT INTO thread_test (value) VALUES (?)", ("ok",))

            result = {}

            def worker():
                result["row"] = database.fetchOne("SELECT value FROM thread_test LIMIT 1")

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(timeout=5)
            database.close()

            self.assertFalse(thread.is_alive())
            self.assertEqual(result["row"]["value"], "ok")


if __name__ == "__main__":
    unittest.main()
