"""
Aura Assistant
Memory Manager Module

Handles long-term memory for the Aura assistant.

Responsibilities
----------------
- Store persistent user information
- Retrieve stored memory
- Automatically extract memory from conversation using the LLM
- Persist memory across sessions using SQLite
"""

import json
import requests


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
        self.config = context.config

        # LLM settings for memory extraction
        self.endpoint = self.config.require("llm.endpoint")
        self.model = self.config.require("llm.model")

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
                value TEXT,
                importance INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


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

        try:
            prompt = f"""
You are Aura's memory extraction system.

Extract long-term personal facts about the user.

Return JSON only.

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

Message:
{text}
"""
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(self.endpoint, json=payload)
            if response.status_code != 200:
                if self.logger:
                    self.logger.warning(
                        f"Memory extraction API error: {response.text}"
                    )
                return

            data = response.json()
            raw = data.get("response", "").strip()
            if self.logger:
                self.logger.debug(f"Memory extractor raw output: {raw}")
            if not raw:
                return

            try:
                extracted = json.loads(raw)
            except json.JSONDecodeError:
                if self.logger:
                    self.logger.warning("Memory extractor returned invalid JSON")
                return

            if not isinstance(extracted, dict):
                return
            for key, value in extracted.items():
                if not key or value is None:
                    continue

                if len(str(value)) > 200:
                    continue

                self.setMemory(key, str(value))
                if self.logger:
                    self.logger.info(f"Learned memory: {key} = {value}")
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
            INSERT INTO memory (key, value, importance)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET
                value = excluded.value,
                importance = excluded.importance,
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
