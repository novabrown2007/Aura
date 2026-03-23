import unittest

from modules.llm.conversationHistory import ConversationHistory
from tests.support.fakes import InMemoryDatabase, make_context


class ConversationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.database = InMemoryDatabase()
        self.context = make_context(database=self.database)
        self.history = ConversationHistory(self.context)

    def test_add_and_get_recent_messages(self):
        self.history.logMessage("user", "hello")
        self.history.logMessage("aura", "hi there")
        self.history.logMessage("user", "what time is it")

        recent = self.history.getRecentMessages(limit=2)

        self.assertEqual(
            recent,
            [("aura", "hi there"), ("user", "what time is it")],
        )

    def test_invalid_author_raises(self):
        with self.assertRaises(ValueError):
            self.history.logMessage("assistant", "bad role")

    def test_clear_removes_messages(self):
        self.history.logMessage("user", "persist me")
        self.assertEqual(len(self.history.getRecentMessages(limit=10)), 1)

        self.history.clear()

        self.assertEqual(self.history.getRecentMessages(limit=10), [])


if __name__ == "__main__":
    unittest.main()

