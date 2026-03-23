from typing import Any, Optional, Tuple

import mysql.connector


class MySQLDatabase:
    """
    MySQL database interface for the Aura assistant.

    This class is designed to match the existing database interface:
    - connect()
    - close()
    - execute(query, params)
    - fetchOne(query, params)
    - fetchAll(query, params)
    - initialize()
    """

    def __init__(self, context):
        self.context = context

        self.host = self.context.config.require("database.host")
        self.port = self.context.config.get("database.port", 3306)
        self.user = self.context.config.require("database.user")
        self.password = self.context.config.require("database.password")
        self.database_name = self.context.config.require("database.name")

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Database")

        self.connection: Optional[mysql.connector.MySQLConnection] = None

        if self.logger:
            self.logger.info("MySQL initialized.")

    # --------------------------------------------------
    # Connection Management
    # --------------------------------------------------

    def connect(self):
        """
        Establish a connection to the MySQL database.
        """

        if self.connection is not None and self.connection.is_connected():
            return

        self.connection = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database_name,
        )

        if self.logger:
            self.logger.info(
                f"MySQL connected: '{self.user}@{self.host}:{self.port}/{self.database_name}'."
            )

    def close(self):
        """
        Close the database connection.
        """

        if self.connection:
            self.connection.close()
            self.connection = None

            if self.logger:
                self.logger.info("MySQL connection closed.")

    # --------------------------------------------------
    # Query Execution
    # --------------------------------------------------

    def execute(self, query: str, params: Tuple = ()):
        """
        Execute a query without returning results.
        """

        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(self._normalizeQuery(query), self._normalizeParams(params))
        self.connection.commit()
        return cursor

    def fetchOne(self, query: str, params: Tuple = ()):
        """
        Execute a query and return a single row.
        """

        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(self._normalizeQuery(query), self._normalizeParams(params))
        return cursor.fetchone()

    def fetchAll(self, query: str, params: Tuple = ()):
        """
        Execute a query and return all rows.
        """

        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(self._normalizeQuery(query), self._normalizeParams(params))
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
                `key` VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
            """
        )

    def _normalizeQuery(self, query: str) -> str:
        """
        Convert generic question-mark placeholders to MySQL placeholders.
        """

        return query.replace("?", "%s")

    @staticmethod
    def _normalizeParams(params: Tuple[Any, ...]):
        """
        Ensure params are always passed as a tuple/list.
        """

        if params is None:
            return ()
        return params
