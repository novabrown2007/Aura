"""Integration tests for live MySQL connectivity and basic database behavior."""

import os
import unittest
from types import SimpleNamespace


def _env_true(name: str) -> bool:
    """Return True when an environment variable is explicitly set to true-ish."""

    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


class MySQLIntegrationTests(unittest.TestCase):
    """Validates MySQLDatabase against a real MySQL server when enabled."""

    def setUp(self):
        """Skip unless explicitly enabled and build config from environment values."""

        if not _env_true("RUN_LIVE_MYSQL_TEST"):
            self.skipTest("Set RUN_LIVE_MYSQL_TEST=true to run live MySQL integration tests.")

        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        self.db_name = os.getenv("DB_NAME", "aura")
        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "")

    def _make_context(self):
        """Create a minimal runtime-like context object expected by MySQLDatabase."""

        config_data = {
            "database": {
                "host": self.db_host,
                "port": self.db_port,
                "name": self.db_name,
                "user": self.db_user,
                "password": self.db_password,
            }
        }

        class Config:
            """Tiny config adapter exposing get/require methods for tests."""

            def __init__(self, data):
                self._data = data

            def get(self, key, default=None):
                value = self._data
                for part in key.split("."):
                    if not isinstance(value, dict) or part not in value:
                        return default
                    value = value[part]
                return value

            def require(self, key):
                value = self.get(key)
                if value is None:
                    raise KeyError(f"Missing config key: {key}")
                return value

        return SimpleNamespace(logger=None, config=Config(config_data))

    def test_connect_initialize_and_roundtrip_query(self):
        """Connect, initialize schema, and validate basic query/CRUD flow."""

        try:
            from modules.database.mysql.mysqlDatabase import MySQLDatabase
        except ModuleNotFoundError as error:
            self.skipTest(f"MySQL driver unavailable: {error}")

        database = MySQLDatabase(self._make_context())
        database.connect()
        database.initialize()

        ping = database.fetchOne("SELECT 1 AS ok")
        self.assertIsNotNone(ping)
        self.assertEqual(int(ping["ok"]), 1)

        table_name = "integration_test_runtime"
        database.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                label VARCHAR(255) NOT NULL
            )
            """
        )
        database.execute(f"INSERT INTO {table_name} (label) VALUES (?)", ("smoke",))
        row = database.fetchOne(f"SELECT label FROM {table_name} ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(row)
        self.assertEqual(row["label"], "smoke")

        database.execute(f"DROP TABLE IF EXISTS {table_name}")
        database.close()

