"""Utilities for assembling provider-neutral prompts."""

from __future__ import annotations

from typing import Any


class PromptBuilder:
    """Build clean prompt sections without binding callers to a provider."""

    @staticmethod
    def buildSystemPrompt(
        basePrompt: str,
        memory: dict[str, Any] | None = None,
        toolDefinitions: list[dict[str, Any]] | None = None,
    ) -> str:
        """Merge Aura's system prompt with optional memory and tool metadata."""

        sections = [basePrompt.strip()]

        if memory:
            memoryLines = ["Known user information:"]
            for key, value in memory.items():
                memoryLines.append(f"- {key}: {value}")
            sections.append("\n".join(memoryLines))

        if toolDefinitions:
            toolLines = ["Available tool definitions:"]
            for tool in toolDefinitions:
                toolLines.append(f"- {tool.get('name')}: {tool.get('description', '')}")
            sections.append("\n".join(toolLines))

        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def buildConversationHistory(conversationHistory: list | None = None) -> str:
        """Format conversation history from tuple or dict message shapes."""

        if not conversationHistory:
            return ""

        lines = []
        for message in conversationHistory:
            if isinstance(message, dict):
                role = str(message.get("role") or message.get("author") or "user")
                content = str(message.get("content") or "")
            else:
                role, content = message
                role = str(role)
                content = str(content)
            label = "Aura" if role.lower() in {"aura", "assistant"} else "User"
            lines.append(f"{label}: {content}")
        return "\n".join(lines)

    @classmethod
    def buildPrompt(
        cls,
        systemPrompt: str,
        userPrompt: str,
        conversationHistory: list | None = None,
    ) -> str:
        """Build the final plain-text prompt used by simple completion APIs."""

        historyText = cls.buildConversationHistory(conversationHistory)
        sections = [systemPrompt.strip()]
        if historyText:
            sections.append(f"Previous conversation:\n{historyText}")
        sections.append(f"User: {userPrompt}\nAura:")
        return "\n\n".join(section for section in sections if section)

