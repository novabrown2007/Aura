"""Tests for Aura's layered architecture structure."""

from __future__ import annotations

from pathlib import Path
import unittest


class ArchitectureTests(unittest.TestCase):
    """Validate new top-level packages and architecture documentation."""

    root = Path(__file__).resolve().parents[2]

    def test_architecture_document_exists_and_describes_layers(self):
        path = self.root / "ARCHITECTURE.md"
        text = path.read_text(encoding="utf-8")

        self.assertIn("assistant/", text)
        self.assertIn("interface/", text)
        self.assertIn("providers/", text)

    def test_canonical_layer_packages_import(self):
        from core.modules import AuraModule as CoreAuraModule
        from core.modules import ModuleAction, ModuleCapability, ModuleContext, ModuleIntent, ModuleManager, ModuleMetadata, ModulePermissions, ModuleRegistry, ModuleState
        from core.modules.moduleLoader import ModuleLoader as FrameworkModuleLoader
        from assistant.conversation import ConversationManager
        from assistant.conversation import ConversationHistory
        from assistant.personality import PersonalityManager
        from assistant.memory import MemoryManager
        from providers.base import LLMProvider, ProviderCapabilities
        from providers.gemini import GeminiProvider
        from providers.ollama import OllamaProvider
        from providers.speech.whisperProvider import WhisperProvider
        from providers.speech.piperProvider import PiperProvider
        from interface.voice.vad import VADManager
        from interface.voice.wakeWord import WakeWordManager
        from modules.weather import WeatherModule
        from modules.spotify import SpotifyModule
        from modules.smartHome import SmartHomeModule
        from assistant.conversation.conversationStateManager import ConversationStateManager
        from assistant.personality.personalityManager import PersonalityManager as CanonicalPersonalityManager
        from assistant.memory.memoryManager import MemoryManager as CanonicalMemoryManager
        from assistant.memory.memoryStore import MemoryStore
        from assistant.memory.memoryRetriever import MemoryRetriever
        from assistant.memory.summarizer import MemorySummarizer

        self.assertIsNotNone(ConversationManager)
        self.assertIsNotNone(ConversationHistory)
        self.assertIsNotNone(PersonalityManager)
        self.assertIsNotNone(MemoryManager)
        self.assertIsNotNone(CoreAuraModule)
        self.assertIsNotNone(ModuleAction)
        self.assertIsNotNone(ModuleCapability)
        self.assertIsNotNone(ModuleContext)
        self.assertIsNotNone(ModuleIntent)
        self.assertIsNotNone(ModuleManager)
        self.assertIsNotNone(ModuleMetadata)
        self.assertIsNotNone(ModulePermissions)
        self.assertIsNotNone(ModuleRegistry)
        self.assertIsNotNone(ModuleState)
        self.assertIsNotNone(FrameworkModuleLoader)
        self.assertIsNotNone(ConversationStateManager)
        self.assertIsNotNone(CanonicalPersonalityManager)
        self.assertIsNotNone(CanonicalMemoryManager)
        self.assertIsNotNone(LLMProvider)
        self.assertIsNotNone(ProviderCapabilities)
        self.assertIsNotNone(GeminiProvider)
        self.assertIsNotNone(OllamaProvider)
        self.assertIsNotNone(WhisperProvider)
        self.assertIsNotNone(PiperProvider)
        self.assertIsNotNone(VADManager)
        self.assertIsNotNone(WakeWordManager)
        self.assertIsNotNone(WeatherModule)
        self.assertIsNotNone(SpotifyModule)
        self.assertIsNotNone(SmartHomeModule)
        self.assertIsNotNone(MemoryStore)
        self.assertIsNotNone(MemoryRetriever)
        self.assertIsNotNone(MemorySummarizer)

    def test_layer_packages_are_present_on_disk(self):
        for relative in [
            "assistant",
            "assistant/conversation",
            "assistant/personality",
            "assistant/memory",
            "interface/voice/vad",
            "interface/voice/wakeWord",
            "providers",
            "core/modules",
            "modules/weather",
            "modules/spotify",
            "modules/smartHome",
            "providers/speech",
        ]:
            self.assertTrue((self.root / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()
