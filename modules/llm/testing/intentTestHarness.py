"""Reusable test harness for structured intent parsing cases."""

from __future__ import annotations

from typing import Any


class IntentTestHarness:
    """Run repeatable intent parser assertions against an IntentPipeline."""

    def __init__(self, pipeline, systemPrompt: str = "You are Aura."):
        """Store the pipeline under test."""

        self.pipeline = pipeline
        self.systemPrompt = systemPrompt

    def testIntent(
        self,
        userInput: str,
        expectedTool: str,
        expectedArgs: dict[str, Any] | None = None,
        conversationHistory: list | None = None,
    ) -> dict[str, Any]:
        """Parse one user input and compare it with the expected tool and args."""

        parsed = self.pipeline.parseIntent(userInput, self.systemPrompt, conversationHistory)
        if not parsed.get("success"):
            return {
                "success": False,
                "error": parsed.get("error"),
                "userInput": userInput,
            }

        intent = parsed["intent"]
        expectedArgs = expectedArgs or {}
        mismatches = []
        if intent.intent != expectedTool:
            mismatches.append(f"Expected tool {expectedTool}, got {intent.intent}.")
        for key, value in expectedArgs.items():
            if intent.arguments.get(key) != value:
                mismatches.append(f"Expected argument {key}={value!r}, got {intent.arguments.get(key)!r}.")

        return {
            "success": not mismatches,
            "userInput": userInput,
            "expectedTool": expectedTool,
            "expectedArgs": expectedArgs,
            "actualTool": intent.intent,
            "actualArgs": intent.arguments,
            "confidence": intent.confidence,
            "errors": mismatches,
        }

    def testToolChain(
        self,
        userInput: str,
        expectedSteps: list[dict[str, Any]],
        conversationHistory: list | None = None,
    ) -> dict[str, Any]:
        """Parse one user input and compare it with an ordered tool chain."""

        parsed = self.pipeline.parseIntents(userInput, self.systemPrompt, conversationHistory)
        if not parsed.get("success"):
            return {
                "success": False,
                "error": parsed.get("error"),
                "userInput": userInput,
            }

        intents = parsed["intents"]
        mismatches = []
        if len(intents) != len(expectedSteps):
            mismatches.append(f"Expected {len(expectedSteps)} steps, got {len(intents)}.")

        for index, expectedStep in enumerate(expectedSteps):
            if index >= len(intents):
                break
            intent = intents[index]
            expectedTool = expectedStep.get("tool")
            expectedArgs = expectedStep.get("arguments", {})
            if intent.intent != expectedTool:
                mismatches.append(f"Step {index}: expected tool {expectedTool}, got {intent.intent}.")
            for key, value in expectedArgs.items():
                if intent.arguments.get(key) != value:
                    mismatches.append(
                        f"Step {index}: expected argument {key}={value!r}, "
                        f"got {intent.arguments.get(key)!r}."
                    )

        return {
            "success": not mismatches,
            "userInput": userInput,
            "expectedSteps": expectedSteps,
            "actualSteps": [intent.asDict() for intent in intents],
            "errors": mismatches,
        }
