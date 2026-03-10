class MemoryManager:
    """
    Manages long-term memory for the Aura assistant.

    The MemoryManager stores persistent key-value information about
    the user, system configuration, or other long-term knowledge
    that should be included in LLM prompts.

    Memory is stored in the database so it persists across sessions.
    """

    def __init__(self, context):
        """
        Initialize the memory manager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Memory")

        self.database = context.database

        self._initializeDatabase()

        if self.logger:
            self.logger.info("Initialized")

    # --------------------------------------------------
    # Database Setup
    # --------------------------------------------------

    def _initializeDatabase(self):
        """
        Create the memory table if it does not exist.
        """

        if not self.database:
            return

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

    # --------------------------------------------------
    # Memory Access
    # --------------------------------------------------

    def setMemory(self, key: str, value: str):
        """
        Store a memory entry.

        Args:
            key (str):
                Memory key.

            value (str):
                Memory value.
        """

        if not self.database:
            return

        self.database.execute(
            """
            INSERT OR REPLACE INTO memory (key, value)
            VALUES (?, ?)
            """,
            (key, value)
        )

        if self.logger:
            self.logger.debug(f"Memory updated: {key}")

    def getMemory(self):
        """
        Retrieve all stored memory.

        Returns:
            dict:
                Dictionary of memory entries.
        """

        if not self.database:
            return {}

        rows = self.database.fetchAll(
            "SELECT key, value FROM memory"
        )

        memory = {}

        for row in rows:
            memory[row["key"]] = row["value"]

        return memory

    def get(self, key: str):
        """
        Retrieve a single memory value.

        Args:
            key (str)

        Returns:
            str | None
        """

        if not self.database:
            return None

        row = self.database.fetchOne(
            "SELECT value FROM memory WHERE key = ?",
            (key,)
        )

        if row:
            return row["value"]

        return None

    def delete(self, key: str):
        """
        Remove a memory entry.

        Args:
            key (str)
        """

        if not self.database:
            return

        self.database.execute(
            "DELETE FROM memory WHERE key = ?",
            (key,)
        )

        if self.logger:
            self.logger.debug(f"Memory deleted: {key}")

    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------

    def clear(self):
        """
        Clear all stored memory.
        """

        if not self.database:
            return

        self.database.execute(
            "DELETE FROM memory"
        )

        if self.logger:
            self.logger.warning("All memory cleared")
