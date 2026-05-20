"""Automated tests for `test_memory_manager` behavior and regression coverage."""

import unittest
from types import SimpleNamespace

from modules.llm.memoryManager import MemoryManager
from modules.llm.models.llmResponse import LLMResponse
from tests.support.fakes import InMemoryDatabase, make_context


class MemoryManagerTests(unittest.TestCase):
    """Test cases covering `MemoryManagerTests` behavior and expected command/runtime outcomes."""
    def setUp(self):
        """Prepare the test fixture state before each test case executes."""
        self.database = InMemoryDatabase()
        self.context = make_context(database=self.database)
        self.context.llmManager = SimpleNamespace(
            generateStructuredResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                rawResponse={},
            )
        )
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

    def test_learn_from_message_persists_extracted_values(self):
        """Validate that learn from message persists extracted values behaves as expected."""
        captured = []
        self.context.llmManager = SimpleNamespace(
            generateStructuredResponse=lambda *args, **kwargs: (
                captured.append(args),
                LLMResponse(
                    provider="test",
                    success=True,
                    rawResponse={"name": "Nova", "favorite_food": "pizza"},
                ),
            )[1]
            )
        self.memory.llmManager = self.context.llmManager

        self.memory.learnFromMessage("My name is Nova and I like pizza.")

        all_memory = self.memory.getMemory()
        self.assertEqual(all_memory.get("name"), "Nova")
        self.assertEqual(all_memory.get("favorite_food"), "pizza")
        self.assertIn("Conversation:", captured[0][1])

    def test_learn_from_history_sends_short_term_history_to_llm(self):
        """Memory extraction should send the short-term history window as context."""

        captured = []
        self.context.llmManager = SimpleNamespace(
            generateStructuredResponse=lambda *args, **kwargs: (
                captured.append((args, kwargs)),
                LLMResponse(
                    provider="test",
                    success=True,
                    rawResponse={"favorite_color": "purple"},
                ),
            )[1]
        )
        self.memory.llmManager = self.context.llmManager

        self.memory.learnFromHistory([("user", "I like purple"), ("aura", "Noted")])

        prompt = captured[0][0][1]
        self.assertIn("User: I like purple", prompt)
        self.assertIn("Aura: Noted", prompt)
        self.assertEqual(self.memory.get("favorite_color"), "purple")

    def test_learn_from_message_ignores_invalid_json(self):
        """Validate that learn from message ignores invalid json behaves as expected."""
        self.context.llmManager = SimpleNamespace(
            generateStructuredResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=False,
                error="invalid json",
            )
        )
        self.memory.llmManager = self.context.llmManager

        self.memory.learnFromMessage("This should fail JSON parse.")

        self.assertEqual(self.memory.getMemory(), {})


if __name__ == "__main__":
    unittest.main()

