"""Tests for tuned memory retrieval and prompt injection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from auraassistant.core.memory import MemoryManager, MemoryQuery
from modules.llm.llmHandler import LLMHandler
from tests.support.fakes import make_context


class MemoryRetrievalTuningTests(unittest.TestCase):
    """Validate contextual retrieval behavior and prompt-safe injection."""

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
            "maxInjectionCount": 3,
            "maxInjectionCharacters": 260,
            "recencyWeight": 0.18,
            "importanceWeight": 0.24,
            "duplicateFiltering": True,
            "compressionEnabled": True,
            "minRelevance": 0.12,
            "retrievalDebug": True,
        }
        self.memory = MemoryManager(self.context)

    def tearDown(self):
        self.memory.shutdown()
        self.tempDir.cleanup()

    def test_contextual_retrieval_prioritizes_relevant_voice_memories(self):
        self.memory.createMemory("projects", "Aura voice pipeline", "Nova is developing the Aura voice pipeline.", tags=["voice", "aura"], importance=0.9)
        self.memory.createMemory("assistant_context", "Push-to-talk", "Nova recently implemented push-to-talk support.", tags=["voice", "ptt"], importance=0.85)
        self.memory.createMemory("preferences", "Response style", "Nova prefers concise responses.", tags=["style"], importance=0.8)
        self.memory.createMemory("locations", "Office", "Nova sometimes works from the office.", tags=["office"], importance=0.9)

        result = self.memory.retrieveContext("I'm still working on the voice system.")
        injectedTitles = [item.memory.title for item in result.injectedMemories]

        self.assertIn("Aura voice pipeline", injectedTitles)
        self.assertIn("Push-to-talk", injectedTitles)
        self.assertNotIn("Office", injectedTitles)
        self.assertIn("[MEMORY RETRIEVAL]", result.debugOutput)
        self.assertIn("Injected:", result.debugOutput)

    def test_duplicate_filtering_and_context_budget_limit_injection(self):
        content = "Nova implemented Faster-Whisper speech-to-text for the Aura voice loop."
        self.memory.createMemory("projects", "Voice STT", content, tags=["voice", "stt"], importance=0.9)
        self.memory.createMemory("conversation_summaries", "Voice STT duplicate", content, tags=["voice", "stt"], importance=0.8)
        self.memory.createMemory(
            "projects",
            "Verbose voice work",
            "Nova is working on a long voice-system task. " * 20,
            tags=["voice"],
            importance=0.7,
        )

        result = self.memory.retrieveContext("voice speech to text")

        rendered = "\n".join(result.renderedLines)
        self.assertEqual(sum(1 for item in result.injectedMemories if "STT" in item.memory.title), 1)
        self.assertLessEqual(len(result.memorySection), self.context.config.get("memory.maxInjectionCharacters") + 40)
        self.assertNotIn("long voice-system task. Nova is working on a long voice-system task", rendered)

    def test_prompt_injection_uses_relevant_context_section(self):
        self.memory.createMemory("preferences", "Response style", "Nova prefers concise responses.", tags=["concise"], importance=0.9)

        injected, result = self.memory.injectPrompt("Base system prompt.", "Please keep this concise.")

        self.assertIn("Base system prompt.", injected)
        self.assertIn("Relevant Context:", injected)
        self.assertIn("Nova prefers concise responses.", injected)
        self.assertGreaterEqual(result.tokenEstimate, 1)

    def test_llm_system_prompt_uses_tuned_memory_injection(self):
        self.memory.createMemory("projects", "Aura voice pipeline", "Nova is developing the Aura voice pipeline.", tags=["voice"], importance=0.9)
        self.context.memoryManager = self.memory
        self.context.conversationHistory = SimpleNamespace(getRecentMessages=lambda limit=25: [])
        self.context.llmManager = SimpleNamespace(offlineMode=True)
        self.context.toolOrchestrator = SimpleNamespace(exportSchemas=lambda offlineMode=False: [])

        handler = LLMHandler()
        handler.initialize(self.context)
        prompt = handler._buildSystemPrompt("What is next on the voice work?")

        self.assertIn("Relevant Context:", prompt)
        self.assertIn("Aura voice pipeline", prompt)
        self.assertNotIn("Known user information:", prompt)

    def test_empty_retrieval_fails_safe(self):
        result = self.memory.retrieveContext("no matching memory")

        self.assertEqual(result.injectedMemories, [])
        self.assertEqual(result.memorySection, "")
        self.assertIn("Retrieved: 0 memories", result.debugOutput)
        self.assertEqual(self.memory.getContext("no matching memory"), {})


if __name__ == "__main__":
    unittest.main()
