"""Tests for Aura LLM prompt profile construction."""

import unittest

from modules.llm.utils.promptBuilder import PromptBuilder


class PromptBuilderTests(unittest.TestCase):
    """Validate that different LLM tasks receive different prompt instructions."""

    def test_conversation_prompt_profile_is_user_facing(self):
        """Conversation prompts should prioritize natural replies."""

        prompt = PromptBuilder.buildSystemPrompt("You are Aura.", profile="conversation")

        self.assertIn("Prompt mode: conversation", prompt)
        self.assertIn("direct user-facing replies", prompt)
        self.assertNotIn("Prompt mode: intent parsing", prompt)

    def test_intent_prompt_profile_is_structured(self):
        """Intent prompts should demand structured intent JSON."""

        prompt = PromptBuilder.buildIntentPrompt("You are Aura.", confidenceThreshold=0.8)

        self.assertIn("Prompt mode: intent parsing", prompt)
        self.assertIn("Return exactly one JSON object", prompt)
        self.assertIn("Use less than 0.8 when unsure", prompt)

    def test_memory_summary_prompt_profile_extracts_durable_facts(self):
        """Memory prompts should be strict extraction prompts."""

        prompt = PromptBuilder.buildMemorySummaryPrompt()

        self.assertIn("Prompt mode: memory summarization", prompt)
        self.assertIn("Extract durable user facts only", prompt)
        self.assertIn("Return only valid JSON", prompt)

    def test_automation_planning_prompt_profile_plans_without_execution(self):
        """Automation planning prompts should plan steps without tool calls."""

        prompt = PromptBuilder.buildAutomationPlanningPrompt(
            "You are Aura.",
            toolDefinitions=[
                {
                    "name": "lights.changed",
                    "description": "React to light changes.",
                    "parameters": {"device_id": {"type": "string"}},
                }
            ],
            runtimeContext={"room": "office"},
        )

        self.assertIn("Prompt mode: automation planning", prompt)
        self.assertIn("ordered tool_steps", prompt)
        self.assertIn("lights.changed", prompt)
        self.assertIn("room: office", prompt)
        self.assertIn("Do not return executable tool-call JSON", prompt)

    def test_tool_selection_prompt_profile_uses_tool_call_contract(self):
        """Tool selection prompts should expose exact tool-call JSON guidance."""

        prompt = PromptBuilder.buildSystemPrompt(
            "You are Aura.",
            toolDefinitions=[
                {
                    "name": "schedule.createItem",
                    "description": "Create schedule item.",
                    "parameters": {"title": {"type": "string"}},
                }
            ],
            profile="toolSelection",
        )

        self.assertIn("Prompt mode: tool selection", prompt)
        self.assertIn("Available deterministic tools", prompt)
        self.assertIn('"toolCalls"', prompt)
        self.assertIn("schedule.createItem", prompt)


if __name__ == "__main__":
    unittest.main()
