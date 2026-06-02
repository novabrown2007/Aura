"""Automated tests for `test_conversation_history` behavior and regression coverage."""

import unittest
from types import SimpleNamespace

from modules.llm.conversationHistory import ConversationHistory
from testing.tests.support.fakes import InMemoryDatabase, make_context


class ConversationHistoryTests(unittest.TestCase):
    """Test cases covering `ConversationHistoryTests` behavior and expected command/runtime outcomes."""
    def setUp(self):
        """Prepare the test fixture state before each test case executes."""
        self.database = InMemoryDatabase()
        self.context = make_context(database=self.database)
        self.history = ConversationHistory(self.context)

    def test_add_and_get_recent_messages(self):
        """Validate that add and get recent messages behaves as expected."""
        self.history.logMessage("user", "hello")
        self.history.logMessage("aura", "hi there")
        self.history.logMessage("user", "what time is it")

        recent = self.history.getRecentMessages(limit=2)

        self.assertEqual(
            recent,
            [("aura", "hi there"), ("user", "what time is it")],
        )

    def test_recent_messages_are_filtered_by_conversation(self):
        """Each chat should keep its own conversation history."""

        self.history.logMessage("user", "hello", conversationId="chat-1")
        self.history.logMessage("aura", "hi there", conversationId="chat-1")
        self.history.logMessage("user", "separate chat", conversationId="chat-2")

        self.assertEqual(
            self.history.getRecentMessages(limit=10, conversationId="chat-1"),
            [("user", "hello"), ("aura", "hi there")],
        )
        self.assertEqual(
            self.history.getRecentMessages(limit=10, conversationId="chat-2"),
            [("user", "separate chat")],
        )

    def test_invalid_author_raises(self):
        """Validate that invalid author raises behaves as expected."""
        with self.assertRaises(ValueError):
            self.history.logMessage("assistant", "bad role")

    def test_clear_removes_messages(self):
        """Validate that clear removes messages behaves as expected."""
        self.history.logMessage("user", "persist me")
        self.assertEqual(len(self.history.getRecentMessages(limit=10)), 1)

        self.history.clear()

        self.assertEqual(self.history.getRecentMessages(limit=10), [])

    def test_history_persists_across_restarts_by_default(self):
        """Conversation history should survive restarts unless disabled explicitly."""

        self.history.logMessage("user", "old message")
        self.assertEqual(len(self.history.getRecentMessages(limit=10)), 1)

        restarted = ConversationHistory(self.context)

        self.assertEqual(restarted.getRecentMessages(limit=10), [("user", "old message")])

    def test_history_can_persist_across_restarts_when_configured(self):
        """Persistence remains available behind an explicit config switch."""

        self.context.config._data["llm"]["history"]["persistAcrossRestarts"] = True
        self.history = ConversationHistory(self.context)
        self.history.logMessage("user", "keep me")

        restarted = ConversationHistory(self.context)

        self.assertEqual(restarted.getRecentMessages(limit=10), [("user", "keep me")])

    def test_history_limit_comes_from_config(self):
        """Conversation history should roll over at the configured limit."""

        self.context.config._data["llm"]["history"]["limit"] = 3
        self.history = ConversationHistory(self.context)

        for index in range(5):
            self.history.logMessage("user", f"message {index}")

        self.assertEqual(
            self.history.getRecentMessages(limit=10),
            [
                ("user", "message 2"),
                ("user", "message 3"),
                ("user", "message 4"),
            ],
        )

    def test_memory_frequency_comes_from_config(self):
        """Memory extraction should trigger after the configured message count."""

        calls = []
        self.context.config._data["llm"]["history"]["limit"] = 4
        self.context.config._data["llm"]["memory"]["frequency"] = 3
        self.context.memoryManager = SimpleNamespace(
            learnFromHistory=lambda messages: calls.append(list(messages))
        )
        self.history = ConversationHistory(self.context)

        self.history.logMessage("user", "one")
        self.history.logMessage("aura", "two")
        self.assertEqual(calls, [])

        self.history.logMessage("user", "three")

        self.assertEqual(
            calls,
            [[("user", "one"), ("aura", "two"), ("user", "three")]],
        )


if __name__ == "__main__":
    unittest.main()

