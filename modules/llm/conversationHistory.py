class ConversationHistory:
    """
    Manages conversation history for Aura.

    This class stores user and assistant messages so the LLM
    can maintain conversational context between prompts.

    Messages are stored in the database and can also be cached
    in memory for fast access.
    """

    def __init__(self, context):
        """
        Initialize the conversation history manager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("ConversationHistory")

        self.database = context.database

        self._initializeDatabase()

        if self.logger:
            self.logger.info("Initialized")

    # --------------------------------------------------
    # Database Setup
    # --------------------------------------------------

    def _initializeDatabase(self):
        """
        Create conversation history table if it does not exist.
        """

        if not self.database:
            return

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

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

        if self.logger:
            self.logger.debug(f"Logged message from {author}")


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
