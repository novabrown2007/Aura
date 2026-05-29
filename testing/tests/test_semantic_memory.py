"""Tests for Aura semantic memory retrieval and embeddings."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from assistant.memory.models import MemoryEmbedding
from assistant.memory.storage import SQLiteEmbeddingStore
from providers.embeddings import LocalEmbeddingProvider
from modules.llm.memory import MemoryManager, MemoryQuery
from testing.tests.support.fakes import make_context


class SemanticMemoryTests(unittest.TestCase):
    """Validate semantic embeddings, hybrid retrieval, and prompt injection."""

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
            "injectionEnabled": True,
            "maxInjectionCount": 5,
            "maxInjectionCharacters": 512,
            "semantic": {
                "enabled": True,
                "provider": "gemini",
                "model": "text-embedding-004",
                "maxResults": 5,
                "minimumSimilarity": 0.2,
                "recencyWeight": 0.2,
                "importanceWeight": 0.2,
                "similarityWeight": 0.6,
                "autoIndex": True,
            },
        }
        self.memory = MemoryManager(self.context)

    def tearDown(self):
        self.memory.shutdown()
        self.tempDir.cleanup()

    def test_local_embedding_provider_generates_deterministic_vectors(self):
        provider = LocalEmbeddingProvider(self.context)
        provider.initialize()

        first = provider.embedText("Working on the voice pipeline")
        second = provider.embedText("Developing the Aura voice pipeline")

        self.assertTrue(provider.isAvailable())
        self.assertEqual(len(first), len(second))
        self.assertGreater(provider.cosineSimilarity(first, second), 0.2)

    def test_memory_manager_indexes_and_retrieves_by_meaning(self):
        """A query about recent work should retrieve relevant project memories."""

        self.memory.createMemory(
            "projects",
            "Aura voice pipeline",
            "Nova is developing the Aura voice pipeline.",
            tags=["voice", "pipeline", "work"],
            importance=0.9,
        )
        self.memory.createMemory(
            "preferences",
            "Preferred verbosity",
            "Nova prefers concise responses.",
            tags=["style"],
            importance=0.7,
        )

        results = self.memory.retrieveRelevantMemories("What was I working on yesterday?", limit=3)
        top = results[0]

        self.assertEqual(top["memory"]["title"], "Aura voice pipeline")
        self.assertIn("semantic", top["matchedBy"])
        self.assertGreater(top["relevanceScore"], 0.2)
        self.assertEqual(self.memory.semanticMemoryState()["provider"], "local")
        self.assertGreaterEqual(self.memory.semanticMemoryState()["indexedCount"], 2)

    def test_prompt_injection_uses_semantic_context(self):
        self.memory.createMemory(
            "projects",
            "Aura voice pipeline",
            "Nova is developing the Aura voice pipeline.",
            tags=["voice", "pipeline", "work"],
            importance=0.9,
        )
        self.memory.createMemory(
            "locations",
            "Office",
            "Nova sometimes works from the office.",
            tags=["office"],
            importance=0.4,
        )

        injected, result = self.memory.injectPrompt("Base system prompt.", "What was I working on yesterday?")

        self.assertIn("Base system prompt.", injected)
        self.assertIn("Relevant Context:", injected)
        self.assertIn("Aura voice pipeline", injected)
        self.assertIn("semantic", result.debugOutput.lower())
        self.assertGreater(result.tokenEstimate, 0)

    def test_sqlite_embedding_store_persists_vectors(self):
        store = SQLiteEmbeddingStore(self.dbPath, context=self.context)
        try:
            embedding = MemoryEmbedding(
                memoryId="memory-1",
                provider="local",
                model="local-hash-128",
                vector=[0.1, 0.2, 0.3],
                metadata={"title": "Aura voice pipeline"},
            )
            store.upsertEmbedding(embedding)

            reopened = SQLiteEmbeddingStore(self.dbPath, context=self.context)
            try:
                loaded = reopened.getEmbeddingByMemoryId("memory-1")
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.provider, "local")
                self.assertEqual(loaded.vector, [0.1, 0.2, 0.3])
            finally:
                reopened.close()
        finally:
            store.close()

    def test_memory_query_compatibility_remains_intact(self):
        self.memory.createMemory("projects", "Aura voice pipeline", "Nova is developing the Aura voice pipeline.", tags=["voice"], importance=0.9)
        results = self.memory.retrieveMemories(MemoryQuery(keywords="voice", limit=1))
        self.assertEqual(results[0].title, "Aura voice pipeline")


if __name__ == "__main__":
    unittest.main()
