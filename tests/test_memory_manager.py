"""Automated tests for `test_memory_manager` behavior and regression coverage."""

import unittest
from unittest.mock import patch

from modules.llm.memoryManager import MemoryManager
from tests.support.fakes import InMemoryDatabase, make_context


class DummyResponse:
    """Testing utility class used to simulate `DummyResponse` dependencies and behavior."""
    def __init__(self, status_code=200, payload=None, text=""):
        """Initialize `DummyResponse` with required dependencies and internal state."""
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        """Implement `json` as part of this component's public/internal behavior."""
        return self._payload


class MemoryManagerTests(unittest.TestCase):
    """Test cases covering `MemoryManagerTests` behavior and expected command/runtime outcomes."""
    def setUp(self):
        """Prepare the test fixture state before each test case executes."""
        self.database = InMemoryDatabase()
        self.context = make_context(database=self.database)
        self.memory = MemoryManager(self.context)

    def test_set_get_delete_memory(self):
        """Validate that set get delete memory behaves as expected."""
        self.memory.setMemory("name", "Nova", importance=3)
        self.assertEqual(self.memory.get("name"), "Nova")

        all_memory = self.memory.getMemory()
        self.assertEqual(all_memory, {"name": "Nova"})

        self.memory.delete("name")
        self.assertIsNone(self.memory.get("name"))

    def test_upsert_overwrites_existing_value(self):
        """Validate that upsert overwrites existing value behaves as expected."""
        self.memory.setMemory("favorite_color", "blue")
        self.memory.setMemory("favorite_color", "green")
        self.assertEqual(self.memory.get("favorite_color"), "green")

    @patch("modules.llm.memoryManager.requests.post")
    def test_learn_from_message_persists_extracted_values(self, mock_post):
        """Validate that learn from message persists extracted values behaves as expected."""
        mock_post.return_value = DummyResponse(
            200,
            {"response": '{"name":"Nova","favorite_food":"pizza"}'},
        )

        self.memory.learnFromMessage("My name is Nova and I like pizza.")

        all_memory = self.memory.getMemory()
        self.assertEqual(all_memory.get("name"), "Nova")
        self.assertEqual(all_memory.get("favorite_food"), "pizza")

    @patch("modules.llm.memoryManager.requests.post")
    def test_learn_from_message_ignores_invalid_json(self, mock_post):
        """Validate that learn from message ignores invalid json behaves as expected."""
        mock_post.return_value = DummyResponse(200, {"response": "not json"})

        self.memory.learnFromMessage("This should fail JSON parse.")

        self.assertEqual(self.memory.getMemory(), {})


if __name__ == "__main__":
    unittest.main()

