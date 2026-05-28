"""SQLite fallback database adapter for Aura."""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional, Tuple

from modules.base import AuraModule, ModuleMetadata
from modules.database.databaseTableManager import DatabaseTableManager


class SQLiteCursor:
    """Small cursor wrapper that returns dict rows like the MySQL adapter."""

    def __init__(self, cursor: sqlite3.Cursor, lock: threading.RLock | None = None):
        """Store the raw SQLite cursor."""

        self.cursor = cursor
        self.lock = lock
        self.lastrowid = cursor.lastrowid

    def fetchone(self):
        """Return one row as a dict."""

        if self.lock is None:
            row = self.cursor.fetchone()
        else:
            with self.lock:
                row = self.cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        """Return all rows as dicts."""

        if self.lock is None:
            rows = self.cursor.fetchall()
        else:
            with self.lock:
                rows = self.cursor.fetchall()
        return [dict(row) for row in rows]


class SQLiteDatabase(AuraModule):
    """
    SQLite database adapter used when MySQL is unavailable.

    The adapter accepts the project's MySQL-flavored schema/query strings and
    normalizes the small subset that SQLite cannot parse.
    """

    metadata = ModuleMetadata(
        name="sqliteDatabase",
        version="1.1.0",
        description="SQLite fallback database adapter for Aura persistence.",
        permissions=("filesystem:read", "filesystem:write", "database:read", "database:write"),
        capabilities=("database", "sqlite"),
    )

    def __init__(self, context=None, database_path: Optional[str] = None):
        """Initialize the adapter with a local database path."""

        super().__init__()
        self.database_path = Path(database_path or "aura.sqlite3")
        self.connection: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self.logger = None
        self.database_name = str(self.database_path)
        self._configured_database_path = database_path
        if context is not None:
            self.initialize(context)

    def initialize(self, context=None):
        """Initialize from context or create schema when already configured."""

        if context is None:
            return self.initializeSchema()

        super().initialize(context)
        self.context = context
        configured_path = None
        if getattr(context, "config", None) is not None:
            configured_path = context.config.get("database.sqlite_path")

        self.database_path = Path(self._configured_database_path or configured_path or "aura.sqlite3")
        self.logger = context.logger.getChild("SQLiteDatabase") if context.logger else None
        self.database_name = str(self.database_path)

    def connect(self):
        """Open the SQLite database file."""

        if self.connection is not None:
            return

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.database_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

        if self.logger:
            self._logStartup(f"sqliteDatabase module started: database_path='{self.database_path}'.")

    def close(self):
        """Close the SQLite connection."""

        if self.connection is not None:
            with self._lock:
                self.connection.close()
                self.connection = None
            if self.logger:
                self.logger.info("SQLite connection closed.")

    def initializeSchema(self):
        """Initialize the Aura schema in SQLite."""

        if self.logger:
            self.logger.info("Initializing SQLite schema.")
        DatabaseTableManager(self).createAllTables()

    def execute(self, query: str, params: Tuple = ()):
        """Execute one query and commit changes."""

        with self._lock:
            cursor = self._execute(query, params)
            self.connection.commit()
        return cursor

    def fetchOne(self, query: str, params: Tuple = ()):
        """Fetch one row."""

        return self._execute(query, params).fetchone()

    def fetchAll(self, query: str, params: Tuple = ()):
        """Fetch all rows."""

        return self._execute(query, params).fetchall()

    def _execute(self, query: str, params: Tuple = ()):
        """Normalize and execute a query."""

        if self.connection is None:
            raise RuntimeError("SQLite database is not connected.")

        normalized_query = self._normalizeQuery(query)
        normalized_params = self._normalizeParams(params)

        try:
            with self._lock:
                cursor = self.connection.cursor()
                cursor.execute(normalized_query, normalized_params)
                return SQLiteCursor(cursor, self._lock)
        except sqlite3.OperationalError as error:
            if self._isDuplicateColumnAdd(normalized_query, error):
                with self._lock:
                    return SQLiteCursor(self.connection.cursor(), self._lock)
            raise

    def _normalizeQuery(self, query: str) -> str:
        """Translate MySQL-flavored SQL into SQLite-compatible SQL."""

        normalized = query.strip()
        normalized = normalized.replace("`", "")
        normalized = normalized.replace("?", "?")
        normalized = re.sub(r"\bINT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bVARCHAR\s*\(\s*\d+\s*\)", "TEXT", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bDATETIME\b", "TEXT", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bBOOLEAN\b", "INTEGER", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bNOW\s*\(\s*\)", "CURRENT_TIMESTAMP", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+ON\s+UPDATE\s+CURRENT_TIMESTAMP", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\b", "ADD COLUMN", normalized, flags=re.IGNORECASE)
        return normalized

    @staticmethod
    def _normalizeParams(params: Tuple[Any, ...]):
        """Return params in a DB-API-compatible shape."""

        if params is None:
            return ()
        return params

    @staticmethod
    def _isDuplicateColumnAdd(query: str, error: sqlite3.OperationalError) -> bool:
        """Return whether an ALTER ADD COLUMN failed because it already exists."""

        return query.lower().startswith("alter table") and "duplicate column name" in str(error).lower()
