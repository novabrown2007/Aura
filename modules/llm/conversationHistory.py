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
        self.persistAcrossRestarts = bool(config.get("llm.history.persistAcrossRestarts", True))

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

    def add(self, role: str, content: str, conversationId: str = "default"):
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

        conversationId = self._normalizeConversationId(conversationId)
        self.database.execute(
            """
            INSERT INTO conversation_history (conversation_id, role, content)
            VALUES (?, ?, ?)
            """,
            (conversationId, role, content)
        )
        self._trimToHistoryLimit(conversationId)

    def getRecentMessages(self, limit: int = 15, conversationId: str | None = None):
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

        conversationId = self._normalizeConversationId(conversationId) if conversationId is not None else None
        if conversationId:
            rows = self.database.fetchAll(
                """
                SELECT role, content
                FROM conversation_history
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversationId, limit)
            )
        else:
            rows = self.database.fetchAll(
                """
                SELECT role, content
                FROM conversation_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )

        rows.reverse()

        return [(row["role"], row["content"]) for row in rows]

    def getConversationMessages(self, conversationId: str):
        """Return the full message list for a single conversation."""

        if not self.database:
            return []

        conversationId = self._normalizeConversationId(conversationId)
        rows = self.database.fetchAll(
            """
            SELECT role, content
            FROM conversation_history
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversationId,),
        )
        return [(row["role"], row["content"]) for row in rows]

    def listConversationIds(self) -> list[str]:
        """Return all known conversation IDs ordered by most recent activity."""

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT conversation_id, role, content
            FROM conversation_history
            ORDER BY id DESC
            """
        )
        seen: set[str] = set()
        ordered: list[str] = []
        for row in rows:
            conversation_id = self._normalizeConversationId(row.get("conversation_id"))
            if conversation_id in seen:
                continue
            seen.add(conversation_id)
            ordered.append(conversation_id)
        return ordered

    def logMessage(self, author: str, content: str, conversationId: str = "default"):
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

        self.add(author, content, conversationId=conversationId)
        self.loggedSinceMemory += 1

        if self.logger:
            self.logger.debug(f"Logged message from {author}")

        self._maybeTriggerMemoryExtraction()


    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------

    def clear(self, conversationId: str | None = None):
        """
        Clear the conversation history.
        """

        if not self.database:
            return

        if conversationId is None:
            self.database.execute(
                "DELETE FROM conversation_history"
            )
        else:
            self.database.execute(
                "DELETE FROM conversation_history WHERE conversation_id = ?",
                (self._normalizeConversationId(conversationId),),
            )

        if self.logger:
            self.logger.info("Conversation history cleared")

    def _trimToHistoryLimit(self, conversationId: str = "default"):
        """Keep only the configured number of short-term history messages."""

        if not self.database or self.historyLimit <= 0:
            return

        self.database.execute(
            """
            DELETE FROM conversation_history
            WHERE conversation_id = ?
              AND id NOT IN (
                SELECT id FROM (
                    SELECT id
                    FROM conversation_history
                    WHERE conversation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) AS recent_history
            )
            """,
            (conversationId, conversationId, self.historyLimit),
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

    @staticmethod
    def _normalizeConversationId(conversationId: str | None) -> str:
        value = str(conversationId or "default").strip()
        return value or "default"
