"""Centralized database table creation for Aura."""


class DatabaseTableManager:
    """
    Creates and maintains all core Aura database tables.

    This class is the single place where CREATE TABLE statements live.
    """

    def __init__(self, database):
        """
        Initialize the table manager with a database interface.

        Args:
            database:
                Active database adapter with an `execute()` method.
        """

        self.database = database

    def createAllTables(self):
        """
        Create every required Aura table if it does not already exist.
        """

        self.createSystemInfoTable()
        self.createCommandLogsTable()
        self.createConversationHistoryTable()
        self.createMemoryTable()
        self.createRemindersTable()

    def createSystemInfoTable(self):
        """Create the system_info table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS system_info (
                `key` VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
            """
        )

    def createCommandLogsTable(self):
        """Create the command_logs table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS command_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_text TEXT NOT NULL,
                command_root VARCHAR(128),
                status VARCHAR(32) NOT NULL,
                response_text TEXT,
                error_text TEXT,
                duration_ms INT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createConversationHistoryTable(self):
        """Create the conversation_history table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                role VARCHAR(32) NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createMemoryTable(self):
        """Create the memory table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                memory_key VARCHAR(255) PRIMARY KEY,
                value TEXT,
                importance INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createRemindersTable(self):
        """Create the reminders table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                remind_at DATETIME NULL,
                delivered_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.database.execute(
            """
            ALTER TABLE reminders
            ADD COLUMN IF NOT EXISTS delivered_at DATETIME NULL
            """
        )
