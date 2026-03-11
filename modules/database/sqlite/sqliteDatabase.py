import sqlite3
from typing import Optional, List, Tuple


class SQLiteDatabase:
    """
    SQLite database interface for the Aura assistant.

    This class provides a simple wrapper around the sqlite3 module,
    handling connection management and common query operations.

    The database is intended to be initialized during system startup
    and stored in the RuntimeContext.
    """

    def __init__(self, context):
        """
        Initialize the SQLite database connection.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        self.db_path = self.context.config.require("database.path")

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Database")

        self.connection: Optional[sqlite3.Connection] = None

        if self.logger:
            self.logger.info(f"sqliteDatabase.py has been initialized.")

    # --------------------------------------------------
    # Connection Management
    # --------------------------------------------------

    def connect(self):
        """
        Establish a connection to the SQLite database.
        """

        if self.connection is not None:
            return

        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

        if self.logger:
            self.logger.info(f"SQLite connected: {self.db_path}")

    def close(self):
        """
        Close the database connection.
        """

        if self.connection:
            self.connection.close()
            self.connection = None

            if self.logger:
                self.logger.info("SQLite connection closed")

    # --------------------------------------------------
    # Query Execution
    # --------------------------------------------------

    def execute(self, query: str, params: Tuple = ()):
        """
        Execute a query without returning results.

        Args:
            query (str):
                SQL query.

            params (tuple):
                Query parameters.
        """

        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()

        return cursor

    def fetchOne(self, query: str, params: Tuple = ()):
        """
        Execute a query and return a single row.

        Args:
            query (str)
            params (tuple)

        Returns:
            sqlite3.Row | None
        """

        cursor = self.connection.cursor()
        cursor.execute(query, params)

        return cursor.fetchone()

    def fetchAll(self, query: str, params: Tuple = ()):
        """
        Execute a query and return all rows.

        Args:
            query (str)
            params (tuple)

        Returns:
            list[sqlite3.Row]
        """

        cursor = self.connection.cursor()
        cursor.execute(query, params)

        return cursor.fetchall()

    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def initialize(self):
        """
        Initialize base database schema required by Aura.
        """

        if self.logger:
            self.logger.info("Initializing database schema")

        self.execute(
            """
            CREATE TABLE IF NOT EXISTS system_info (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
