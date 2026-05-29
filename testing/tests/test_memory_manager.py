"""Tests for Aura's structured long-term memory layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.llm.memory import Memory, MemoryCategory, MemoryManager, MemoryQuery
from core.threading.events.eventManager import EventManager
from testing.tests.support.fakes import make_context


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

    def test_single_profile_message_is_split_into_atomic_memories(self):
        """One dense profile message should create separate structured facts."""

        message = (
            "My birthday is March 22nd, 2007, and I like writing dates in dd/mm/yyyy. "
            "My favorite colour is purple. I'm 19 years old. "
            "I am omnisexual, non-binaring questioning MTF, and polyamorous."
        )

        memories = self.memory.learnFromMessage(message, sessionId="profile")

        contents = {memory.content for memory in memories}
        self.assertIn("Nova's birthday is March 22nd, 2007.", contents)
        self.assertIn("Nova prefers dates in dd/mm/yyyy.", contents)
        self.assertIn("Nova's favorite color is purple.", contents)
        self.assertIn("Nova is 19 years old.", contents)
        self.assertIn("Nova's sexual orientation is omnisexual.", contents)
        self.assertIn("Nova's gender identity is non-binary questioning MTF.", contents)
        self.assertIn("Nova's relationship orientation is polyamorous.", contents)
        self.assertGreaterEqual(len(memories), 7)

    def test_conversation_summary_stores_atomic_profile_facts(self):
        """Conversation summarization should not persist dense profile blobs as facts."""

        self.memory.summarizeConversation(
            [
                (
                    "user",
                    "My birthday is March 22nd, 2007, and I like writing dates in dd/mm/yyyy. "
                    "My favorite colour is purple. I'm 19 years old. "
                    "I am omnisexual, non-binaring questioning MTF, and polyamorous.",
                )
            ],
            sessionId="summary-profile",
        )

        stored = self.memory.retrieveMemories(MemoryQuery(categories=["preferences"], limit=20))
        contents = {memory.content for memory in stored}
        self.assertIn("Nova's birthday is March 22nd, 2007.", contents)
        self.assertIn("Nova prefers dates in dd/mm/yyyy.", contents)
        self.assertIn("Nova's gender identity is non-binary questioning MTF.", contents)
        self.assertNotIn(
            "My birthday is March 22nd, 2007, and I like writing dates in dd/mm/yyyy. My favorite colour is purple. I'm 19 years old. I am omnisexual, non-binaring questioning MTF, and polyamorous.",
            contents,
        )

    def test_questions_are_not_saved_as_conversation_facts(self):
        """Profile questions should be answered from memory, not stored as facts."""

        memories = self.memory.learnFromMessage("What is my romantic orientation?", sessionId="profile")
        self.memory.summarizeConversation(
            [("user", "What is my gender identity?")],
            sessionId="question-summary",
        )

        stored = self.memory.retrieveMemories(MemoryQuery(limit=20))
        contents = {memory.content for memory in stored}
        self.assertIsNone(memories)
        self.assertNotIn("What is my romantic orientation?", contents)
        self.assertNotIn("What is my gender identity?", contents)

    def test_name_statements_are_stored_as_canonical_profile_facts(self):
        """Raw name messages should not be stored as people-memory transcripts."""

        memories = self.memory.learnFromMessage("Hello, my name is Nova Brown", sessionId="profile")

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].category, "people")
        self.assertEqual(memories[0].title, "Name")
        self.assertEqual(memories[0].content, "Nova's name is Nova Brown.")

    def test_duplicate_profile_facts_are_merged(self):
        """Repeated durable facts should update one memory instead of creating copies."""

        first = self.memory.createMemory(
            "preferences",
            "Nova's relationship orientation is polyamorous",
            "Nova's relationship orientation is polyamorous.",
            tags=["profile"],
            source="conversation.fact",
        )
        second = self.memory.createMemory(
            "preferences",
            "Nova's relationship orientation is polyamorous",
            "Nova's relationship orientation is polyamorous.",
            tags=["relationship_orientation"],
            source="conversation.fact",
        )

        stored = self.memory.retrieveMemories(MemoryQuery(categories=["preferences"], limit=20))
        matches = [memory for memory in stored if memory.content == "Nova's relationship orientation is polyamorous."]
        self.assertEqual(first.memoryId, second.memoryId)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].tags, ["profile", "relationship_orientation"])

    def test_same_fact_title_updates_changed_content(self):
        """A changed profile value should replace the old value instead of duplicating it."""

        first = self.memory.createMemory(
            "preferences",
            "Relationship orientation",
            "Nova's relationship orientation is polyamorous.",
            tags=["relationship_orientation"],
        )
        second = self.memory.createMemory(
            "preferences",
            "Relationship orientation",
            "Nova's relationship orientation is monogamous.",
            tags=["relationship_orientation"],
        )

        stored = self.memory.retrieveMemories(MemoryQuery(categories=["preferences"], limit=20))
        contents = {memory.content for memory in stored}
        self.assertEqual(first.memoryId, second.memoryId)
        self.assertIn("Nova's relationship orientation is monogamous.", contents)
        self.assertNotIn("Nova's relationship orientation is polyamorous.", contents)

    def test_startup_compacts_existing_duplicate_and_question_memories(self):
        """Existing noisy memory rows should be cleaned when the manager starts."""

        self.memory.store.upsertMemory(
            Memory(
                category="preferences",
                title="Nova's relationship orientation is polyamorous",
                content="Nova's relationship orientation is polyamorous.",
                source="conversation.fact",
            )
        )
        self.memory.store.upsertMemory(
            Memory(
                category="preferences",
                title="Relationship orientation duplicate",
                content="Nova's relationship orientation is polyamorous.",
                source="conversation.fact",
            )
        )
        self.memory.store.upsertMemory(
            Memory(
                category="preferences",
                title="What is my romantic orientation?",
                content="What is my romantic orientation?",
                source="conversation.fact",
            )
        )
        self.memory.store.upsertMemory(
            Memory(
                category="people",
                title="Name",
                content="Nova's name is Nova.",
                tags=["profile", "name"],
                source="profile.statement",
                createdAt="2026-05-20T00:00:00+00:00",
            )
        )
        self.memory.store.upsertMemory(
            Memory(
                category="people",
                title="Hello, my name is Nova Brown",
                content="Hello, my name is Nova Brown",
                source="conversation.fact",
                createdAt="2026-05-21T00:00:00+00:00",
            )
        )
        self.memory.shutdown()

        restarted = MemoryManager(self.context)
        try:
            stored = restarted.retrieveMemories(MemoryQuery(categories=["preferences"], limit=20))
            contents = [memory.content for memory in stored]
            self.assertEqual(contents.count("Nova's relationship orientation is polyamorous."), 1)
            self.assertNotIn("What is my romantic orientation?", contents)
            people = restarted.retrieveMemories(MemoryQuery(categories=["people"], limit=20))
            self.assertEqual([memory.content for memory in people], ["Nova's name is Nova Brown."])
        finally:
            restarted.shutdown()
            self.memory = restarted

    def test_startup_removes_subsumed_conversation_summaries(self):
        """Rolling summary prefixes should not accumulate as separate memories."""

        self.memory.store.upsertMemory(
            Memory(
                category="conversation_summaries",
                title="Conversation summary",
                content="Hello, how are you? What time is it?",
                source="conversation.ended",
            )
        )
        self.memory.store.upsertMemory(
            Memory(
                category="conversation_summaries",
                title="Conversation summary",
                content="Hello, how are you? What time is it? My birthday is March 22nd, 2007.",
                source="conversation.ended",
            )
        )
        self.memory.shutdown()

        restarted = MemoryManager(self.context)
        try:
            summaries = restarted.retrieveMemories(MemoryQuery(categories=["conversation_summaries"], limit=20))
            contents = [memory.content for memory in summaries]
            self.assertEqual(contents, ["Hello, how are you? What time is it? My birthday is March 22nd, 2007."])
        finally:
            restarted.shutdown()
            self.memory = restarted

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
