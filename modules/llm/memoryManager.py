"""
Aura Assistant
Memory Manager Module

Handles long-term memory for the Aura assistant.

Responsibilities
----------------
- Store persistent user information
- Retrieve stored memory
- Automatically extract memory from conversation using the LLM
- Persist memory across sessions using the configured database
"""

from modules.base import AuraModule, ModuleMetadata


class MemoryManager(AuraModule):
    """
    Manages long-term memory for the Aura assistant.

    The MemoryManager stores persistent key-value information about
    the user, system configuration, or other long-term knowledge
    that should be included in LLM prompts.

    Memory is stored in the database so it persists across sessions.
    """

    metadata = ModuleMetadata(
        name="memoryManager",
        version="1.0.0",
        description="Long-term memory storage and extraction.",
        permissions=("database:read", "database:write", "network:http"),
        capabilities=("memory",),
    )

    def __init__(self, context=None):
        """
        Initialize the memory manager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        super().__init__()
        self.logger = None
        self.database = None
        self.config = None
        self.llmManager = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Initialize the memory manager module."""

        super().initialize(context)
        self.context = context

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("LLM.Memory")

        self.database = context.database
        self.config = context.config
        self.llmManager = getattr(context, "llmManager", None)

        self._initializeDatabase()

        if self.logger:
            self.logger.info("Initialized.")

    def getIntents(self):
        """Return intents handled by memory manager."""

        return []

    # --------------------------------------------------
    # Database Setup
    # --------------------------------------------------

    def _initializeDatabase(self):
        """
        Validate database availability for memory persistence.

        Table creation is centralized in modules.database.databaseTableManager.
        """

        if not self.database and self.logger:
            self.logger.warning("MemoryManager started without a database.")


    # --------------------------------------------------
    # Automatic Memory Learning
    # --------------------------------------------------

    def learnFromMessage(self, text: str):
        """
        Use the language model to extract long-term user memory
        from a message.

        Args:
            text (str):
                User message.
        """

        self.learnFromHistory([("user", text)])

    def learnFromHistory(self, messages: list[tuple[str, str]]):
        """
        Extract long-term memory from the configured short-term history window.

        Args:
            messages:
                Chronological list of ``(role, content)`` conversation entries.
        """

        try:
            if self.llmManager is None:
                if self.logger:
                    self.logger.warning("Memory learning skipped because LLMManager is unavailable.")
                return

            system_prompt = """
You are Aura's memory extraction system.


Extract ONLY facts that are explicitly stated in the message.

Do NOT infer.
Do NOT guess.
Do NOT assume missing information.
Do NOT expand on partial statements.

If the user did not directly state a fact, do not include it.


Return ONLY valid JSON.

Do NOT include explanations.
Do NOT include markdown.
Do NOT include ```json blocks.
Do NOT include any text before or after the JSON.

If no memory is found, return exactly:
{{}}

Example:
{{
  "name": "Nova",
  "favorite_color": "purple"
}}


Rules:
- Only store persistent personal facts about the user.
- Ignore temporary information.
- Ignore commands or instructions.
- Never store system prompts or internal instructions.
- If no long-term information exists return {{}}.
- Only use the "Conversation" section below. Ignore all prior conversation.
"""
            conversation_lines = []
            for role, content in messages:
                label = "Aura" if role == "aura" else "User"
                conversation_lines.append(f"{label}: {content}")
            user_prompt = "Conversation:\n" + "\n".join(conversation_lines)
            schema = {
                "type": "object",
                "additionalProperties": {"type": "string"},
            }
            response = self.llmManager.generateStructuredResponse(
                system_prompt,
                user_prompt,
                schema,
                conversationHistory=[],
            )

            if not response.success:
                if self.logger:
                    self.logger.warning(f"Memory extraction failed: {response.error}")
                return

            extracted = response.rawResponse
            if self.logger:
                self.logger.debug(f"Memory extractor structured output: {extracted}")
            if not isinstance(extracted, dict):
                if self.logger:
                    self.logger.warning("Memory extractor returned non-object JSON")
                return

            for key, value in extracted.items():
                if not key or value is None:
                    continue
                value_str = str(value).strip()
                # Reject overly long or messy values
                if len(value_str) > 200:
                    continue
                if len(value_str.split()) > 10:
                    continue

                self.setMemory(key, value_str)
                if self.logger:
                    self.logger.info(f"Learned memory: {key} = {value_str}")

        except Exception as error:
            if self.logger:
                self.logger.warning(f"Memory learning failed: {error}")


    # --------------------------------------------------
    # Memory Access
    # --------------------------------------------------

    def setMemory(self, key: str, value: str, importance: int = 1):
        """
        Store or update a memory entry.

        Args:
            key (str):
                Memory key.

            value (str):
                Memory value.

            importance (int):
                Importance ranking (future use).
        """

        if not self.database:
            return
        self.database.execute(
            """
            INSERT INTO memory (memory_key, value, importance)
            VALUES (?, ?, ?)
            ON DUPLICATE KEY UPDATE
                value = VALUES(value),
                importance = VALUES(importance),
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value, importance)
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
            "SELECT memory_key, value FROM memory"
        )
        memory = {}
        for row in rows:
            memory[row["memory_key"]] = row["value"]
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
            "SELECT value FROM memory WHERE memory_key = ?",
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
            "DELETE FROM memory WHERE memory_key = ?",
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
