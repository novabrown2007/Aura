"""Database integration logic for `mysqlDatabase` in Aura."""

from typing import Any, Optional, Tuple

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from modules.base import AuraModule, ModuleMetadata
from modules.database.databaseTableManager import DatabaseTableManager

MySQLConnectorConnection = MySQLConnectionAbstract | PooledMySQLConnection


class MySQLDatabase(AuraModule):
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

    metadata = ModuleMetadata(
        name="mysqlDatabase",
        version="1.1.0",
        description="MySQL database adapter for Aura persistence.",
        permissions=("database:connect", "database:read", "database:write"),
        capabilities=("database", "mysql"),
    )

    def __init__(self, context=None):
        """Initialize `MySQLDatabase` with required dependencies and internal state."""

        super().__init__()
        self.host = None
        self.port = None
        self.user = None
        self.password = None
        self.database_name = None
        self.connection_timeout = 5
        self.logger = None
        self.connection: Optional[MySQLConnectorConnection] = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context=None):
        """Initialize the adapter from context or create schema when already configured."""

        if context is None:
            return self.initializeSchema()

        super().initialize(context)
        self.context = context

        self.host = self.context.config.require("database.host")
        self.port = self.context.config.get("database.port", 3306)
        self.user = self.context.config.require("database.user")
        self.password = self.context.config.require("database.password")
        self.database_name = self.context.config.require("database.name")
        self.connection_timeout = self.context.config.get("database.connection_timeout", 5)

        if context.logger:
            self.logger = context.logger.getChild("Database")

        if self.logger:
            self._logStartup("mysqlDatabase module started.")

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
            connection_timeout=self.connection_timeout,
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

    def initializeSchema(self):
        """
        Initialize base database schema required by Aura.
        """

        if self.logger:
            self.logger.info("Initializing database schema")

        manager = DatabaseTableManager(self)
        manager.createAllTables()

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
