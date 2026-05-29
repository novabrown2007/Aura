"""Automated tests for `test_llm_handler` behavior and regression coverage."""

import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import requests

from core.tools.tool import Tool
from core.tools.toolExecutor import ToolExecutor
from core.tools.toolRegistry import ToolRegistry
from modules.llm.manager.llmManager import LLMManager
from modules.llm.models.llmResponse import LLMResponse
from modules.llm.llmHandler import LLMHandler
from modules.llm.providers.base.providerCapabilities import ProviderCapabilities
from modules.llm.providers.gemini.geminiProvider import GeminiProvider
from modules.llm.providers.ollama.ollamaProvider import OllamaProvider
from testing.tests.support.fakes import DictConfig


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


class StubHistory:
    """Testing utility class used to simulate `StubHistory` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubHistory` with required dependencies and internal state."""
        self.messages = []

    def getRecentMessages(self, limit=25):
        """Return `getRecentMessages` data from the component's current state."""
        return self.messages[-limit:]

    def logMessage(self, author, content):
        """Implement `logMessage` as part of this component's public/internal behavior."""
        self.messages.append((author, content))


class StubMemory:
    """Testing utility class used to simulate `StubMemory` dependencies and behavior."""
    def __init__(self):
        """Initialize `StubMemory` with required dependencies and internal state."""
        self.learn_inputs = []
        self.memory = {"name": "Nova"}
        self.structuredMemories = []

    def learnFromMessage(self, text):
        """Implement `learnFromMessage` as part of this component's public/internal behavior."""
        self.learn_inputs.append(text)

    def getMemory(self):
        """Return `getMemory` data from the component's current state."""
        return self.memory

    def createMemory(self, category, title, content, **kwargs):
        """Store a lightweight structured memory for handler tests."""

        memory = SimpleNamespace(category=category, title=title, content=content, **kwargs)
        self.structuredMemories.append(memory)
        self.memory[title] = content
        return memory

    def retrieveMemories(self, limit=20, **_kwargs):
        """Return structured memories plus legacy dictionary values."""

        memories = list(self.structuredMemories)
        memories.extend(
            SimpleNamespace(category="preferences", title=key, content=value)
            for key, value in self.memory.items()
        )
        return memories[:limit]


class StubProvider:
    """Small provider stub used to test manager routing behavior."""

    def __init__(self, provider_name, response):
        """Store provider identity and response returned by generation calls."""

        self.providerName = provider_name
        self.response = response
        self.initialized = True
        self.plainCalls = 0
        self.structuredCalls = 0

    def initialize(self):
        """Mark provider initialized."""

        self.initialized = True

    def shutdown(self):
        """Mark provider shutdown."""

        self.initialized = False

    def generateResponse(self, systemPrompt, userPrompt, conversationHistory=None):
        """Return the configured plain response."""

        self.plainCalls += 1
        return self.response

    def generateStructuredResponse(self, systemPrompt, userPrompt, schema, conversationHistory=None):
        """Return the configured structured response."""

        self.structuredCalls += 1
        return self.response


class SequenceProvider:
    """Provider stub that returns responses in order."""

    def __init__(self, provider_name, responses):
        self.providerName = provider_name
        self.responses = list(responses)
        self.initialized = True
        self.model = provider_name

    def initialize(self):
        self.initialized = True

    def shutdown(self):
        self.initialized = False

    def generateResponse(self, *_args, **_kwargs):
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

    def generateStructuredResponse(self, *_args, **_kwargs):
        return self.generateResponse()


def make_llm_context(endpoint="http://localhost:11434/api/generate"):
    """Construct and return a configured helper object for testing/tests/runtime wiring."""
    context = SimpleNamespace()
    context.logger = None
    context.config = DictConfig(
        {
            "llm": {
                "activeProvider": "ollama",
                "fallbackProvider": "gemini",
                "endpoint": endpoint,
                "model": "gemma4:e4b",
                "timeout": 10,
                "retryCount": 1,
                "history": {"enabled": True, "limit": 10},
                "memory": {"enabled": True},
                "providers": {
                    "ollama": {
                        "endpoint": endpoint,
                        "model": "gemma4:e4b",
                    }
                },
            }
        }
    )
    context.conversationHistory = StubHistory()
    context.memoryManager = StubMemory()
    context.modules = {}
    context.toolRegistry = ToolRegistry(context)
    context.toolExecutor = ToolExecutor(context)
    context.toolRegistry.registerTool(
        Tool(
            name="calendar.createEvent",
            description="Create a calendar event.",
            parameters={"title": {"type": "string"}, "start_at": {"type": "string"}},
            requiredParameters=("title", "start_at"),
            module="calendar",
            method="createEvent",
        )
    )
    return context


class LLMHandlerTests(unittest.TestCase):
    """Test cases covering `LLMHandlerTests` behavior and expected command/runtime outcomes."""

    @patch("modules.llm.providers.ollama.ollamaProvider.requests.post")
    def test_generate_response_success(self, mock_post):
        """Validate that generate response success behaves as expected."""
        mock_post.return_value = DummyResponse(200, {"response": "Hello from Aura"})
        handler = LLMHandler(make_llm_context())

        result = handler.generateResponse("Tell me something useful.")

        self.assertEqual(result, "Hello from Aura")
        self.assertEqual(handler.history.messages[-2], ("user", "Tell me something useful."))

    def test_simple_greeting_does_not_call_provider(self):
        """Simple greetings should not spend Gemini calls or trigger fallback."""

        context = make_llm_context()
        calls = []
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda *args, **kwargs: calls.append(args) or LLMResponse(
                provider="test",
                success=True,
                text="Provider hello.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Hello!")

        self.assertEqual(result, "Hello.")
        self.assertEqual(calls, [])
        self.assertEqual(handler.history.messages[-1], ("aura", "Hello."))

    @patch("modules.llm.providers.ollama.ollamaProvider.requests.post")
    def test_generate_response_handles_http_error(self, mock_post):
        """Validate that generate response handles http error behaves as expected."""
        oldGeminiKey = os.environ.pop("GEMINI_API_KEY", None)
        try:
            mock_post.return_value = DummyResponse(500, text="server error")
            handler = LLMHandler(make_llm_context())

            result = handler.generateResponse("Tell me something useful.")

            self.assertIn("can't reach an available language provider", result)
            self.assertIn("server error", result)
        finally:
            if oldGeminiKey is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = oldGeminiKey

    def test_generate_structured_response_uses_manager_validation(self):
        """Structured responses should be parsed and returned as dictionaries."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            generateStructuredResponse=lambda *args, **kwargs: LLMResponse(
                provider="gemini",
                success=True,
                rawResponse={"intent": "calendar.create", "confidence": 1},
            )
        )
        handler = LLMHandler(context)

        result = handler.generateStructuredResponse(
            "Create a calendar event",
            {
                "type": "object",
                "required": ["intent", "confidence"],
                "properties": {
                    "intent": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        )

        self.assertEqual(result["intent"], "calendar.create")
        self.assertEqual(result["confidence"], 1)

    def test_manager_falls_back_when_primary_fails(self):
        """The manager should route to fallback provider after primary failure."""

        context = make_llm_context()
        manager = LLMManager(context)
        manager.providers["primary"] = StubProvider(
            "primary",
            LLMResponse(provider="primary", success=False, error="down"),
        )
        manager.providers["fallback"] = StubProvider(
            "fallback",
            LLMResponse(provider="fallback", success=True, text="Recovered"),
        )
        manager.activeProviderName = "primary"
        manager.preferredProviderName = "primary"
        manager.fallbackProviderName = "fallback"
        manager.offlineMode = False

        response = manager.generateResponse("system", "hello")

        self.assertTrue(response.success)
        self.assertEqual(response.provider, "fallback")
        self.assertEqual(response.text, "Recovered")

    def test_manager_enters_offline_fallback_on_gemini_quota_error(self):
        """Gemini quota failures should stop routing new requests to Gemini."""

        context = make_llm_context()
        manager = LLMManager(context)
        manager.providers["gemini"] = StubProvider(
            "gemini",
            LLMResponse(provider="gemini", success=False, error="429 RESOURCE_EXHAUSTED quota exceeded"),
        )
        manager.providers["ollama"] = StubProvider(
            "ollama",
            LLMResponse(provider="ollama", success=True, text="Recovered locally"),
        )
        manager.activeProviderName = "gemini"
        manager.preferredProviderName = "gemini"
        manager.fallbackProviderName = "ollama"
        manager.offlineMode = False

        response = manager.generateResponse("system", "hello")

        self.assertTrue(response.success)
        self.assertEqual(response.provider, "ollama")
        self.assertEqual(response.text, "Recovered locally")
        self.assertTrue(manager.offlineMode)
        self.assertEqual(manager.activeProviderName, "ollama")
        self.assertIn("quota", manager.offlineReason)

    @patch.object(GeminiProvider, "initialize")
    def test_manager_keeps_ollama_primary_when_gemini_fallback_is_unavailable(self, mock_initialize):
        """Gemini fallback startup failure should not force Ollama into offline mode."""

        mock_initialize.return_value = None
        context = make_llm_context()
        context.config._data["llm"]["fallbackProvider"] = "gemini"
        manager = LLMManager(context)

        self.assertFalse(manager.offlineMode)
        self.assertEqual(manager.activeProviderName, "ollama")
        self.assertEqual(manager.fallbackProviderName, "gemini")

    def test_manager_allows_structured_output_when_fallback_supports_it(self):
        """Gemini fallback should keep tool parsing available after Ollama fails."""

        context = make_llm_context()
        manager = LLMManager(context)
        manager.providers["ollama"] = StubProvider(
            "ollama",
            LLMResponse(provider="ollama", success=False, error="connection refused"),
        )
        manager.providers["gemini"] = StubProvider(
            "gemini",
            LLMResponse(provider="gemini", success=True, text="Recovered"),
        )
        manager.activeProviderName = "ollama"
        manager.preferredProviderName = "ollama"
        manager.fallbackProviderName = "gemini"
        manager.offlineMode = False

        response = manager.generateResponse("system", "hello")

        self.assertTrue(response.success)
        self.assertEqual(response.provider, "gemini")
        self.assertTrue(manager.offlineMode)
        self.assertTrue(manager.canUseStructuredOutput())

    def test_manager_can_fail_closed_without_conversational_fallback(self):
        """A disabled fallback should not route normal chat to Ollama."""

        context = make_llm_context()
        manager = LLMManager(context)
        gemini = StubProvider(
            "gemini",
            LLMResponse(provider="gemini", success=False, error="429 RESOURCE_EXHAUSTED quota exceeded"),
        )
        ollama = StubProvider(
            "ollama",
            LLMResponse(provider="ollama", success=True, text="Hallucinated fallback answer"),
        )
        manager.providers["gemini"] = gemini
        manager.providers["ollama"] = ollama
        manager.activeProviderName = "gemini"
        manager.preferredProviderName = "gemini"
        manager.fallbackProviderName = ""
        manager.offlineMode = False

        first = manager.generateResponse("system", "Tell me something useful.")
        second = manager.generateResponse("system", "Tell me something else.")

        self.assertFalse(first.success)
        self.assertEqual(first.provider, "gemini")
        self.assertFalse(second.success)
        self.assertEqual(second.error, "No LLM provider available.")
        self.assertEqual(gemini.plainCalls, 1)
        self.assertEqual(ollama.plainCalls, 0)
        self.assertTrue(manager.offlineMode)
        self.assertEqual(manager.activeProviderName, "gemini")

    def test_manager_does_not_send_structured_requests_to_untrusted_fallback(self):
        """Quota failures should not create extra structured requests to Ollama."""

        context = make_llm_context()
        manager = LLMManager(context)
        gemini = StubProvider(
            "gemini",
            LLMResponse(provider="gemini", success=False, error="429 RESOURCE_EXHAUSTED quota exceeded"),
        )
        ollama = StubProvider(
            "ollama",
            LLMResponse(provider="ollama", success=True, text='{"intent": "bad.fallback"}'),
        )
        ollama.capabilities = ProviderCapabilities(supportsStructuredOutput=False)
        manager.providers["gemini"] = gemini
        manager.providers["ollama"] = ollama
        manager.activeProviderName = "gemini"
        manager.preferredProviderName = "gemini"
        manager.fallbackProviderName = "ollama"
        manager.offlineMode = False

        response = manager.generateStructuredResponse("system", "Turn on lights", {"type": "object"})

        self.assertFalse(response.success)
        self.assertEqual(response.provider, "gemini")
        self.assertEqual(gemini.structuredCalls, 1)
        self.assertEqual(ollama.structuredCalls, 0)
        self.assertTrue(manager.offlineMode)

    def test_manager_retries_and_restores_preferred_provider_after_cooldown(self):
        """Temporary fallback should retry Gemini after the cooldown expires."""

        context = make_llm_context()
        manager = LLMManager(context)
        manager.providers["gemini"] = SequenceProvider(
            "gemini",
            [
                LLMResponse(provider="gemini", success=False, error="429 RESOURCE_EXHAUSTED retryDelay': '5s'"),
                LLMResponse(provider="gemini", success=True, text="Gemini restored"),
            ],
        )
        manager.providers["ollama"] = StubProvider(
            "ollama",
            LLMResponse(provider="ollama", success=True, text="Fallback"),
        )
        manager.activeProviderName = "gemini"
        manager.preferredProviderName = "gemini"
        manager.fallbackProviderName = "ollama"

        first = manager.generateResponse("system", "hello")
        manager.offlineUntil = 0
        second = manager.generateResponse("system", "hello again")

        self.assertEqual(first.provider, "ollama")
        self.assertEqual(second.provider, "gemini")
        self.assertFalse(manager.offlineMode)
        self.assertEqual(manager.activeProviderName, "gemini")

    @patch.object(GeminiProvider, "initialize")
    def test_manager_uses_ollama_when_gemini_is_unavailable(self, mock_initialize):
        """Gemini startup failure should force offline mode and use Ollama."""

        mock_initialize.return_value = None
        context = make_llm_context()
        context.config._data["llm"]["activeProvider"] = "gemini"
        context.config._data["llm"]["fallbackProvider"] = "ollama"
        manager = LLMManager(context)

        self.assertTrue(manager.offlineMode)
        self.assertEqual(manager.activeProviderName, "ollama")

    def test_gemini_client_initialization_failure_does_not_crash_startup(self):
        """Gemini transport/client failures should mark the provider unavailable."""

        context = make_llm_context()
        context.config._data["llm"]["gemini"] = {
            "api_secret": "test-key",
            "model": "gemini-2.5-flash",
        }
        provider = GeminiProvider(context)

        with patch("google.genai.Client", side_effect=RuntimeError("transport unavailable")):
            provider.initialize()

        self.assertFalse(provider.initialized)
        self.assertIsNone(provider.client)

    def test_ollama_rejects_structured_response_requests(self):
        """Ollama should not be trusted for structured tool or intent parsing."""

        provider = OllamaProvider(make_llm_context())
        provider.initialize()

        response = provider.generateStructuredResponse("system", "user", {"type": "object"})

        self.assertFalse(response.success)
        self.assertIn("offline conversation only", response.error)

    def test_ollama_base_url_is_normalized_to_generate_endpoint(self):
        """Ollama should accept a base URL and post to /api/generate."""

        provider = OllamaProvider(make_llm_context(endpoint="http://localhost:11434"))
        provider.initialize()

        self.assertEqual(provider.endpoint, "http://localhost:11434/api/generate")

    def test_structured_intent_failure_falls_back_to_conversation_reply(self):
        """A structured parse failure should not break normal chat."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            rawLogger=None,
            generateStructuredResponse=lambda *args, **kwargs: LLMResponse(
                provider="gemini",
                success=False,
                error="429 RESOURCE_EXHAUSTED quota exceeded",
            ),
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="ollama",
                success=True,
                text="Hello Nova.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Hello, how are you today?")

        self.assertEqual(result, "Hello Nova.")

    def test_plain_conversation_does_not_use_structured_intent_pipeline(self):
        """Normal chat should not spend structured Gemini calls."""

        context = make_llm_context()
        structuredCalls = []
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            rawLogger=None,
            generateStructuredResponse=lambda *args, **kwargs: structuredCalls.append(args) or LLMResponse(
                provider="gemini",
                success=False,
                error="should not be called",
            ),
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="gemini",
                success=True,
                text="I'm doing well.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Hello, how are you?")

        self.assertEqual(result, "I'm doing well.")
        self.assertEqual(structuredCalls, [])

    def test_tool_request_uses_structured_intent_pipeline(self):
        """Action requests still use the structured tool path."""

        context = make_llm_context()
        structuredCalls = []
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            rawLogger=None,
            generateStructuredResponse=lambda *args, **kwargs: structuredCalls.append(args) or LLMResponse(
                provider="gemini",
                success=True,
                rawResponse={
                    "intent": "lights.turnOn",
                    "arguments": {"room": "bedroom"},
                    "confidence": 0.96,
                    "response": "Turning on the bedroom lights.",
                },
            ),
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="gemini",
                success=True,
                text="Done.",
            ),
        )
        context.toolRegistry.registerTool(
            Tool(
                name="lights.turnOn",
                description="Turn on a light by room.",
                parameters={"room": {"type": "string"}},
                requiredParameters=("room",),
                module="homeAutomation",
                method="turnLightOnByRoom",
            )
        )
        context.homeAutomation = SimpleNamespace(turnLightOnByRoom=lambda **kwargs: {"ok": True})
        handler = LLMHandler(context)

        result = handler.generateResponse("Turn on my bedroom lights")

        self.assertEqual(result, "Done.")
        self.assertEqual(len(structuredCalls), 1)

    def test_profile_age_question_is_answered_deterministically_from_memory(self):
        """Profile age should be calculated from birthday memory, not model math."""

        context = make_llm_context()
        context.memoryManager.memory = {
            "profile": "My birthday is March 22nd, 2007. I'm 19 years old. I am omnisexual."
        }
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="You're 21 years old.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("How old am I?")

        today = date.today()
        expectedAge = today.year - 2007 - ((today.month, today.day) < (3, 22))
        self.assertEqual(result, f"You are {expectedAge} years old.")

    def test_birth_statement_is_stored_before_profile_question_matching(self):
        """Birth statements should be saved, not answered as unrelated profile questions."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="Your name is Nova.",
            ),
        )
        handler = LLMHandler(context)

        statementReply = handler.generateResponse("I was born March 22nd 2007")
        birthdayReply = handler.generateResponse("When was I born?")
        ageReply = handler.generateResponse("how old am I?")

        today = date.today()
        expectedAge = today.year - 2007 - ((today.month, today.day) < (3, 22))
        self.assertEqual(statementReply, "Got it. You were born on March 22nd, 2007.")
        self.assertEqual(birthdayReply, "You were born on March 22nd, 2007.")
        self.assertEqual(ageReply, f"You are {expectedAge} years old.")

    def test_name_statement_updates_memory_instead_of_answering_question(self):
        """A name statement containing 'my name' should not use the name-question branch."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="Your name is Nova.",
            ),
        )
        handler = LLMHandler(context)

        statementReply = handler.generateResponse("Hello, my name is Nova Brown")
        nameReply = handler.generateResponse("What is my name?")

        self.assertEqual(statementReply, "Got it. Your name is Nova Brown.")
        self.assertEqual(nameReply, "Your name is Nova Brown.")

    def test_time_question_uses_local_deterministic_system_time(self):
        """Time questions should not fall through to fallback LLM guesses."""

        context = make_llm_context()
        context.system = SimpleNamespace(getTime=lambda: {"time": "20:12:34"})
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="26 05.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("What time is it?")

        self.assertEqual(result, "It is 20:12.")

    def test_age_statement_updates_memory_instead_of_using_provider(self):
        """Age statements should be stored and acknowledged deterministically."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="Nova Brown, my name is Nova. You're currently 19 years old.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("I'm 19 years old")

        self.assertEqual(result, "Got it. You are 19 years old.")
        self.assertTrue(
            any(memory.content == "Nova is 19 years old." for memory in context.memoryManager.structuredMemories)
        )

    def test_profile_combined_question_separates_sexuality_from_gender_identity(self):
        """Profile summaries should not conflate sexual orientation and gender identity."""

        context = make_llm_context()
        context.memoryManager.memory = {
            "profile": (
                "My birthday is March 22nd, 2007. I'm 19 years old. "
                "I am omnisexual, non-binaring questioning MTF, and polyamorous."
            )
        }
        context.llmManager = SimpleNamespace(offlineMode=True)
        handler = LLMHandler(context)

        result = handler.generateResponse("Tell me my name, age, and sexual orientation.")

        today = date.today()
        expectedAge = today.year - 2007 - ((today.month, today.day) < (3, 22))
        self.assertIn("your name is Nova", result)
        self.assertIn(f"you are {expectedAge} years old", result)
        self.assertIn("your sexual orientation is omnisexual", result)
        self.assertNotIn("MTF", result)

    def test_profile_gender_identity_question_handles_typo_deterministically(self):
        """Gender identity questions should not fall through to provider guesses."""

        context = make_llm_context()
        context.memoryManager.memory = {
            "profile": (
                "My birthday is March 22nd, 2007. I'm 19 years old. "
                "I am omnisexual, non-binaring questioning MTF, and polyamorous."
            )
        }
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text='You prefer to be referred to as "M".',
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("What is my gendre identity")

        self.assertEqual(result, "Your gender identity is non-binary questioning MTF.")

    def test_profile_relationship_orientation_question_is_deterministic(self):
        """Relationship orientation should be separate from sexuality and gender."""

        context = make_llm_context()
        context.memoryManager.memory = {
            "profile": (
                "My birthday is March 22nd, 2007. I'm 19 years old. "
                "I am omnisexual, non-binaring questioning MTF, and polyamorous."
            )
        }
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="I don't know your romantic orientation.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Romantic orientation?")

        self.assertEqual(result, "Your relationship orientation is polyamorous.")

    def test_profile_relationship_orientation_statement_updates_memory(self):
        """Explicit relationship orientation statements should not drift into unrelated memory."""

        context = make_llm_context()
        createdMemories = []
        context.memoryManager.memory = {}
        context.memoryManager.createMemory = (
            lambda category, title, content, **kwargs: createdMemories.append(
                {
                    "category": category,
                    "title": title,
                    "content": content,
                    **kwargs,
                }
            )
        )
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="You prefer dd/mm/yyyy.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("I am polyamorous")

        self.assertEqual(result, "Got it. Your relationship orientation is polyamorous.")
        self.assertEqual(createdMemories[0]["category"], "preferences")
        self.assertEqual(createdMemories[0]["title"], "Relationship orientation")
        self.assertEqual(createdMemories[0]["content"], "Nova's relationship orientation is polyamorous.")

    def test_provider_prefix_is_removed_from_conversation_response(self):
        """Interfaces already label Aura responses, so provider prefixes are stripped."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text="Aura: Hello Nova.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Tell me something useful.")

        self.assertEqual(result, "Hello Nova.")

    def test_offline_without_fallback_does_not_call_ollama_for_conversation(self):
        """When no fallback is configured, Aura should fail closed instead of asking Ollama."""

        context = make_llm_context()
        calls = []
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            fallbackProviderName="",
            providers={},
            canUseStructuredOutput=lambda: False,
            getStatus=lambda: {
                "activeModel": "gemini-2.5-flash",
                "offlineReason": "429 RESOURCE_EXHAUSTED quota exceeded",
            },
            generateResponse=lambda *args, **kwargs: calls.append(args) or LLMResponse(
                provider="ollama",
                success=True,
                text="Bad fallback answer.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Tell me something useful.")

        self.assertIn("I can't reach an available language provider", result)
        self.assertIn("429 RESOURCE_EXHAUSTED", result)
        self.assertEqual(calls, [])

    def test_online_provider_prompt_receives_injected_memory_context(self):
        """All normal provider calls should receive Aura's memory-injected prompt."""

        context = make_llm_context()
        capturedPrompts = []

        def injectPrompt(prompt, userInput, conversationHistory=None):
            return f"{prompt}\n\nRelevant Context:\n- Nova is 19 years old.", {"injected": 1}

        context.memoryManager = SimpleNamespace(injectPrompt=injectPrompt)
        context.llmManager = SimpleNamespace(
            offlineMode=False,
            generateResponse=lambda systemPrompt, *_args, **_kwargs: capturedPrompts.append(systemPrompt)
            or LLMResponse(provider="gemini", success=True, text="Memory-aware response."),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Tell me something useful.")

        self.assertEqual(result, "Memory-aware response.")
        self.assertEqual(len(capturedPrompts), 1)
        self.assertIn("Relevant Context:", capturedPrompts[0])
        self.assertIn("Nova is 19 years old.", capturedPrompts[0])

    def test_offline_fallback_prompt_receives_injected_memory_context(self):
        """Configured fallback providers should receive the same memory context boundary."""

        context = make_llm_context()
        capturedPrompts = []

        def injectPrompt(prompt, userInput, conversationHistory=None):
            return f"{prompt}\n\nRelevant Context:\n- Nova's name is Nova.", {"injected": 1}

        context.memoryManager = SimpleNamespace(injectPrompt=injectPrompt)
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            fallbackProviderName="ollama",
            providers={"ollama": SimpleNamespace(initialized=True)},
            canUseStructuredOutput=lambda: False,
            generateResponse=lambda systemPrompt, *_args, **_kwargs: capturedPrompts.append(systemPrompt)
            or LLMResponse(provider="ollama", success=True, text="Memory-aware fallback response."),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Tell me something useful.")

        self.assertEqual(result, "Memory-aware fallback response.")
        self.assertEqual(len(capturedPrompts), 1)
        self.assertIn("running in offline mode", capturedPrompts[0])
        self.assertIn("Relevant Context:", capturedPrompts[0])
        self.assertIn("Nova's name is Nova.", capturedPrompts[0])

    def test_unknown_profile_question_does_not_fall_through_to_fallback(self):
        """Missing profile facts should be reported locally instead of guessed by fallback."""

        context = make_llm_context()
        calls = []
        context.memoryManager.memory = {}
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            fallbackProviderName="ollama",
            providers={"ollama": SimpleNamespace(initialized=True)},
            canUseStructuredOutput=lambda: False,
            generateResponse=lambda *args, **kwargs: calls.append(args) or LLMResponse(
                provider="ollama",
                success=True,
                text="You are 11.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("And how old am I?")

        self.assertEqual(result, "I don't have your age saved yet.")
        self.assertEqual(calls, [])

    def test_offline_tool_request_reports_tool_path_unavailable(self):
        """Offline fallback should not let Ollama claim Aura cannot control devices."""

        context = make_llm_context()
        calls = []
        context.llmManager = SimpleNamespace(
            offlineMode=True,
            canUseStructuredOutput=lambda: False,
            getStatus=lambda: {
                "activeModel": "gemma4:e4b",
                "offlineReason": "429 RESOURCE_EXHAUSTED quota exceeded",
            },
            generateResponse=lambda *args, **kwargs: calls.append(args) or LLMResponse(
                provider="ollama",
                success=True,
                text="I cannot control devices.",
            ),
        )
        handler = LLMHandler(context)

        result = handler.generateResponse("Turn on my bedroom lights")

        self.assertIn("Gemini tool path", result)
        self.assertIn("temporarily unavailable", result)
        self.assertEqual(calls, [])

    def test_system_prompt_includes_memory_and_tool_contract(self):
        """The generic assistant prompt should expose memory and tool-call rules."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(offlineMode=False)
        handler = LLMHandler(context)

        prompt = handler._buildSystemPrompt()

        self.assertIn("You are Aura, a private AI assistant", prompt)
        self.assertIn("Known user information", prompt)
        self.assertIn("- name: Nova", prompt)
        self.assertIn("Available deterministic tools", prompt)
        self.assertIn("calendar.createEvent", prompt)
        self.assertIn('"toolCalls"', prompt)

    def test_offline_prompt_excludes_tools_and_instructs_generic_action_response(self):
        """Offline prompt should preserve context but avoid executable tools."""

        context = make_llm_context()
        context.llmManager = SimpleNamespace(offlineMode=True)
        handler = LLMHandler(context)

        prompt = handler._buildSystemPrompt()

        self.assertIn("running in offline mode", prompt)
        self.assertIn("Known user information", prompt)
        self.assertIn("- name: Nova", prompt)
        self.assertIn("cannot be completed in offline mode", prompt)
        self.assertNotIn("Available deterministic tools", prompt)
        self.assertNotIn("calendar.createEvent", prompt)
        self.assertNotIn('"toolCalls"', prompt)

    def test_generate_response_executes_calendar_tool_call(self):
        """A JSON tool-call response should execute the matching backend function."""

        calls = []
        context = make_llm_context()
        context.llmManager = SimpleNamespace(
            generateResponse=lambda *args, **kwargs: LLMResponse(
                provider="test",
                success=True,
                text=(
                    '{"response":"Added it to your calendar.",'
                    '"toolCalls":[{"toolName":"calendar.createEvent","arguments":'
                    '{"title":"Dentist","start_at":"2026-05-21 09:00:00"}}]}'
                ),
            )
        )
        context.calendar = SimpleNamespace(
            createEvent=lambda **kwargs: calls.append(kwargs) or 42
        )

        handler = LLMHandler(context)
        result = handler.generateResponse("Add dentist tomorrow at 9")

        self.assertEqual(result, "Added it to your calendar.")
        self.assertEqual(
            calls,
            [{"title": "Dentist", "start_at": "2026-05-21 09:00:00"}],
        )

    def test_live_llm_connection_optional(self):
        """Validate that live llm connection optional behaves as expected."""
        if os.getenv("RUN_LIVE_LLM_TEST", "").lower() != "true":
            self.skipTest("Set RUN_LIVE_LLM_TEST=true to run live LLM connection test.")

        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
        model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

        try:
            response = requests.post(
                endpoint,
                json={"model": model, "prompt": "Reply with: pong", "stream": False},
                timeout=10,
            )
        except requests.RequestException as error:
            self.fail(f"Live LLM request failed: {error}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("response", payload)
        self.assertTrue(str(payload.get("response", "")).strip())


if __name__ == "__main__":
    unittest.main()

