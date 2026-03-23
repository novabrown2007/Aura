"""Automated tests for `test_conversation_history` behavior and regression coverage."""

import unittest

from modules.llm.conversationHistory import ConversationHistory
from tests.support.fakes import InMemoryDatabase, make_context


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


if __name__ == "__main__":
    unittest.main()

