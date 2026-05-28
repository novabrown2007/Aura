"""Language-model integration code for `conversationHistory` in Aura."""

from modules.base import AuraModule, ModuleMetadata


class ConversationHistory(AuraModule):
    """
    Manages conversation history for Aura.

    This class stores user and assistant messages so the LLM
    can maintain conversational context between prompts.

    Messages are stored in the database and can also be cached
    in memory for fast access.
    """

    metadata = ModuleMetadata(
        name="conversationHistory",
        version="1.0.0",
        description="Conversation history persistence for LLM prompts.",
        permissions=("database:read", "database:write"),
        capabilities=("conversation-history",),
    )

    def __init__(self, context=None):
        """
        Initialize the conversation history manager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        super().__init__()
        self.logger = None
        self.database = None
        self.historyLimit = 25
        self.memoryEnabled = True
        self.memoryFrequency = 20
        self.loggedSinceMemory = 0
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Initialize the conversation history module."""

        super().initialize(context)
        self.context = context

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("LLM.ConversationHistory")

        self.database = context.database
        config = context.config
        self.historyLimit = int(config.get("llm.history.limit", 25))
        self.memoryEnabled = bool(config.get("llm.memory.enabled", True))
        self.memoryFrequency = int(config.get("llm.memory.frequency", 20))
        self.persistAcrossRestarts = bool(config.get("llm.history.persistAcrossRestarts", False))

        self._initializeDatabase()
        if not self.persistAcrossRestarts:
            self.clear()

        self._logStartup("conversationHistory module started.")

    def getIntents(self):
        """Return intents handled by conversation history."""

        return []

    # --------------------------------------------------
    # Database Setup
    # --------------------------------------------------

    def _initializeDatabase(self):
        """
        Validate database availability for conversation history access.

        Table creation is centralized in modules.database.databaseTableManager.
        """

        if not self.database and self.logger:
            self.logger.warning("ConversationHistory started without a database.")

    # --------------------------------------------------
    # Message Management
    # --------------------------------------------------

    def add(self, role: str, content: str):
        """
        Add a message to the conversation history.

        Args:
            role (str):
                Message author ("user" or "aura").

            content (str):
                Message text.
        """

        if not self.database:
            return

        self.database.execute(
            """
            INSERT INTO conversation_history (role, content)
            VALUES (?, ?)
            """,
            (role, content)
        )
        self._trimToHistoryLimit()

    def getRecentMessages(self, limit: int = 15):
        """
        Retrieve recent conversation messages.

        Args:
            limit (int):
                Number of messages to retrieve.

        Returns:
            list[tuple]:
                List of (role, content) tuples.
        """

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT role, content
            FROM conversation_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        # reverse to maintain chronological order
        rows.reverse()

        return [(row["role"], row["content"]) for row in rows]

    def logMessage(self, author: str, content: str):
        """
        Log a conversation message.

        This is the primary method used by the assistant to store
        conversation messages in the history database.

        Args:
            author (str):
                Message author ("user" or "aura").

            content (str):
                Message text.
        """

        if author not in ("user", "aura"):
            raise ValueError(f"Invalid message author: {author}")

        self.add(author, content)
        self.loggedSinceMemory += 1

        if self.logger:
            self.logger.debug(f"Logged message from {author}")

        self._maybeTriggerMemoryExtraction()


    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------

    def clear(self):
        """
        Clear the conversation history.
        """

        if not self.database:
            return

        self.database.execute(
            "DELETE FROM conversation_history"
        )

        if self.logger:
            self.logger.info("Conversation history cleared")

    def _trimToHistoryLimit(self):
        """Keep only the configured number of short-term history messages."""

        if not self.database or self.historyLimit <= 0:
            return

        self.database.execute(
            """
            DELETE FROM conversation_history
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id
                    FROM conversation_history
                    ORDER BY id DESC
                    LIMIT ?
                ) AS recent_history
            )
            """,
            (self.historyLimit,),
        )

    def _maybeTriggerMemoryExtraction(self):
        """Run memory extraction after the configured number of logged messages."""

        if not self.memoryEnabled or self.memoryFrequency <= 0:
            return
        if self.loggedSinceMemory < self.memoryFrequency:
            return

        self.loggedSinceMemory = 0
        memoryManager = getattr(self.context, "memoryManager", None)
        if memoryManager is None:
            return

        messages = self.getRecentMessages(limit=self.historyLimit)
        if not messages:
            return

        try:
            memoryManager.learnFromHistory(messages)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Memory extraction from history failed: {error}")
