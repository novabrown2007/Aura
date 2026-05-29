"""Deterministic personality interaction policy."""

from __future__ import annotations

import re


class InteractionPolicy:
    """Enforce command-first assistant behavior."""

    commandVerbs = {
        "turn", "switch", "set", "dim", "brighten", "create", "add", "remind",
        "schedule", "start", "stop", "open", "close", "delete", "update",
        "change", "run", "cancel", "pause", "resume", "send", "email",
    }
    commandObjects = {
        "light", "lights", "lamp", "reminder", "calendar", "event", "task",
        "camera", "stream", "automation", "spotify", "music", "volume",
        "jokes", "humor", "suggestions", "personality", "tone",
    }

    def classifyUserInput(self, userInput: str) -> dict:
        """Return command and personality-control flags for a user message."""

        text = str(userInput or "").strip()
        lowered = text.lower()
        tokens = set(re.findall(r"[a-z0-9_]+", lowered))
        isPersonalityCommand = bool(
            re.search(r"\b(turn|switch|disable|enable|set|make)\b.*\b(jokes?|humou?r|suggestions?|personality|tone)\b", lowered)
            or re.search(r"\b(be|stay)\s+(concise|professional|casual|developer|brief)\b", lowered)
        )
        isCommand = isPersonalityCommand or bool(tokens & self.commandVerbs and tokens & self.commandObjects)
        return {
            "isCommand": isCommand,
            "isPersonalityCommand": isPersonalityCommand,
            "allowsSuggestions": not isCommand,
            "allowsHumor": not isCommand,
            "priority": "command" if isCommand else "conversation",
        }

    def policyText(self) -> str:
        """Return prompt policy text for provider-facing style control."""

        return (
            "Personality policy:\n"
            "- Commands outrank suggestions.\n"
            "- User intent outranks assistant style.\n"
            "- Deterministic execution outranks personality.\n"
            "- Do not claim consciousness, real feelings, personal desires, suffering, or self-preservation.\n"
            "- Keep jokes subtle and never let them interrupt important tasks.\n"
        )

