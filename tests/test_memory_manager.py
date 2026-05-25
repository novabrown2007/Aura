"""Tests for Aura's structured long-term memory layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.memory import MemoryCategory, MemoryManager, MemoryQuery
from core.threading.events.eventManager import EventManager
from tests.support.fakes import make_context


class MemoryManagerTests(unittest.TestCase):
    """Validate structured memory persistence, retrieval, and event updates."""

    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        self.dbPath = str(Path(self.tempDir.name) / "memory.sqlite3")
        self.context = make_context()
        self.context.config._data["memory"] = {
            "enabled": True,
            "databasePath": self.dbPath,
            "maxResults": 8,
            "summaryLength": 180,
            "importanceThreshold": 0.2,
            "autoSummarization": True,
        }
        self.context.eventManager = EventManager(self.context)
        self.memory = MemoryManager(self.context)

    def tearDown(self):
        self.memory.shutdown()
        self.tempDir.cleanup()

    def test_create_retrieve_update_delete_structured_memory(self):
        memory = self.memory.createMemory(
            "preferences",
            "response style",
            "Nova prefers concise responses.",
            tags=["style", "responses"],
            importance=0.8,
        )

        self.assertIsNotNone(memory)
        self.assertEqual(memory.category, MemoryCategory.PREFERENCES.value)
        self.assertEqual(self.memory.getContext("concise responses")["preferences.response_style"], "Nova prefers concise responses.")

        updated = self.memory.updateMemory(memory.memoryId, content="Nova prefers concise technical responses.")
        self.assertEqual(updated.content, "Nova prefers concise technical responses.")

        self.assertTrue(self.memory.deleteMemory(memory.memoryId))
        self.assertEqual(self.memory.searchMemories("concise"), [])

    def test_query_filters_by_category_tag_importance_and_session(self):
        self.memory.createMemory("projects", "Aura voice", "Nova is working on the Aura voice pipeline.", tags=["aura", "voice"], importance=0.9, sessionId="s1")
        self.memory.createMemory("locations", "Office", "Nova works from the office sometimes.", tags=["office"], importance=0.4, sessionId="s2")

        results = self.memory.retrieveMemories(
            MemoryQuery(categories=["projects"], tags=["voice"], minImportance=0.5, sessionId="s1")
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Aura voice")

    def test_search_uses_keyword_and_fuzzy_matching(self):
        self.memory.createMemory("projects", "Aura voice pipeline", "Push-to-talk support is part of the voice work.", tags=["voice"], importance=0.8)

        exact = self.memory.searchMemories("push talk", limit=1)
        fuzzy = self.memory.searchMemories("pipline", limit=1)

        self.assertEqual(exact[0].title, "Aura voice pipeline")
        self.assertEqual(fuzzy[0].title, "Aura voice pipeline")

    def test_conversation_summary_stores_summary_and_facts(self):
        summary = self.memory.summarizeConversation(
            [
                ("user", "I prefer concise responses."),
                ("aura", "Noted."),
                ("user", "I'm working on the Aura voice pipeline."),
            ],
            sessionId="session-1",
        )

        self.assertIsNotNone(summary)
        categories = {memory.category for memory in self.memory.retrieveMemories(MemoryQuery(limit=10))}
        self.assertIn("conversation_summaries", categories)
        self.assertIn("preferences", categories)
        self.assertIn("projects", categories)

    def test_safe_memory_filter_rejects_credentials(self):
        memory = self.memory.createMemory(
            "system_context",
            "api key",
            "My API key is sk-secretsecretsecret",
        )

        self.assertIsNone(memory)
        self.assertEqual(self.memory.retrieveMemories(MemoryQuery()), [])

    def test_event_handler_learns_and_summarizes(self):
        self.context.eventManager.emit("session.created", {"sessionId": "evt"})
        self.context.eventManager.emit("message.received", {"sessionId": "evt", "text": "I prefer concise responses."})
        self.context.eventManager.emit("response.generated", {"sessionId": "evt", "text": "Noted."})
        self.context.eventManager.emit("conversation.ended", {"sessionId": "evt"})

        context = self.memory.getContext("concise", limit=5)

        self.assertTrue(any("concise" in value for value in context.values()))

    def test_sqlite_persistence_survives_manager_restart(self):
        self.memory.createMemory("people", "Nova", "Nova is the primary Aura user.", tags=["nova"], importance=0.9)
        self.memory.shutdown()

        restarted = MemoryManager(self.context)
        try:
            results = restarted.searchMemories("primary user", limit=1)
            self.assertEqual(results[0].title, "Nova")
        finally:
            restarted.shutdown()

    def test_legacy_api_remains_prompt_compatible(self):
        self.memory.setMemory("favorite_color", "purple", importance=3)

        self.assertEqual(self.memory.get("favorite_color"), "purple")
        self.assertEqual(self.memory.getMemory()["favorite_color"], "purple")
        self.assertEqual(self.memory.retrieveRelevantMemories("purple", limit=1)[0]["memory_key"], "favorite_color")
        self.assertEqual(self.memory.summarizeMemories("purple")["favorite_color"], "purple")


if __name__ == "__main__":
    unittest.main()
