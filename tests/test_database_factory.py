"""Tests for database startup fallback behavior."""

import unittest
from unittest.mock import patch

from tests.support.fakes import make_context


class _FakeLogger:
    """Minimal logger used by database factory tests."""

    def __init__(self):
        """Initialize captured log records."""

        self.records = []

    def getChild(self, name):
        """Return this logger for child logging."""

        self.records.append(("child", name))
        return self

    def error(self, message):
        """Record an error log."""

        self.records.append(("error", message))


class _WorkingDatabase:
    """Database stub that connects and initializes successfully."""

    def __init__(self, context):
        """Initialize lifecycle state."""

        self.context = context
        self.connected = False
        self.initialized = False

    def connect(self):
        """Record connection."""

        self.connected = True

    def initialize(self):
        """Record initialization."""

        self.initialized = True


class _FailingDatabase(_WorkingDatabase):
    """Database stub that fails during connection."""

    def connect(self):
        """Raise a connection failure."""

        raise RuntimeError("mysql down")


class DatabaseFactoryTests(unittest.TestCase):
    """Validate MySQL preference and SQLite fallback behavior."""

    @patch("modules.database.databaseFactory.SQLiteDatabase", _WorkingDatabase)
    @patch("modules.database.databaseFactory.MySQLDatabase", _WorkingDatabase)
    def test_prefers_mysql_when_available(self):
        """Factory should return initialized MySQL when it works."""

        from modules.database.databaseFactory import createDatabaseWithFallback

        context = make_context(extra={"logger": _FakeLogger()})
        database = createDatabaseWithFallback(context)

        self.assertTrue(database.connected)
        self.assertTrue(database.initialized)
        self.assertIs(database.context, context)

    @patch("modules.database.databaseFactory.SQLiteDatabase", _WorkingDatabase)
    @patch("modules.database.databaseFactory.MySQLDatabase", _FailingDatabase)
    def test_falls_back_to_sqlite_when_mysql_fails(self):
        """Factory should initialize SQLite after MySQL startup failure."""

        from modules.database.databaseFactory import createDatabaseWithFallback

        logger = _FakeLogger()
        context = make_context(extra={"logger": logger})
        database = createDatabaseWithFallback(context)

        self.assertTrue(database.connected)
        self.assertTrue(database.initialized)
        self.assertTrue(any(record[0] == "error" and "falling back to SQLite" in record[1] for record in logger.records))


if __name__ == "__main__":
    unittest.main()
