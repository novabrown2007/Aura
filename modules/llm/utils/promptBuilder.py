"""Utilities for assembling provider-neutral prompts."""

from __future__ import annotations

from typing import Any

from modules.llm.prompts import PROMPT_PROFILES


class PromptBuilder:
    """Build clean prompt sections without binding callers to a provider."""

    @staticmethod
    def buildSystemPrompt(
        basePrompt: str,
        memory: dict[str, Any] | None = None,
        toolDefinitions: list[dict[str, Any]] | None = None,
        profile: str = "conversation",
    ) -> str:
        """Merge Aura's system prompt with optional memory and tool metadata."""

        profileBuilder = PROMPT_PROFILES.get(profile, PROMPT_PROFILES["conversation"])
        sections = [profileBuilder(basePrompt).strip()]

        if memory:
            memoryLines = ["Known user information:"]
            for key, value in memory.items():
                memoryLines.append(f"- {key}: {value}")
            sections.append("\n".join(memoryLines))

        if toolDefinitions:
            toolLines = [
                "Available deterministic tools:",
                "When a user asks Aura to perform an action, return a JSON object in this exact shape:",
                '{"response":"short user-facing message","toolCalls":[{"toolName":"tool.name","arguments":{}}]}',
                "Use toolCalls only for actions Aura should execute. For normal conversation, answer naturally.",
                "Do not invent tools. Do not claim a tool was executed unless you returned it in toolCalls.",
            ]
            for tool in toolDefinitions:
                arguments = tool.get("arguments") or tool.get("parameters", {})
                toolLines.append(
                    f"- {tool.get('name')}: {tool.get('description', '')} "
                    f"Arguments: {arguments}"
                )
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

    @staticmethod
    def buildIntentPrompt(
        basePrompt: str,
        toolDefinitions: list[dict[str, Any]] | None = None,
        confidenceThreshold: float = 0.75,
        contextualMemory: dict[str, Any] | None = None,
    ) -> str:
        """Build the strict prompt used for structured intent parsing."""

        sections = [
            PROMPT_PROFILES["intentParsing"](basePrompt).strip(),
            (
                "Return exactly one JSON object with this shape:\n"
                '{"response":"","intents":[{"intent":"tool.name","arguments":{},"confidence":0.0,"response":""}]}\n'
                "Use one item in intents for each ordered action the user requested.\n"
                "Each intent must be one registered tool name, or conversation.respond when no tool is needed.\n"
                "Each arguments object must contain only the tool arguments required to execute that step.\n"
                f"confidence must be 0.0 through 1.0. Use less than {confidenceThreshold} when unsure.\n"
                "Do not execute tools. Do not return markdown."
            ),
        ]

        if toolDefinitions:
            toolLines = ["Registered Aura tools:"]
            for tool in toolDefinitions:
                toolLines.append(
                    f"- {tool.get('name')}: {tool.get('description', '')} "
                    f"category={tool.get('category')} parameters={tool.get('parameters')}"
                )
            sections.append("\n".join(toolLines))
        else:
            sections.append("No tools are currently registered. Use conversation.respond.")

        if contextualMemory:
            sections.append(PromptBuilder._formatContextualMemory(contextualMemory))

        return "\n\n".join(sections)

    @staticmethod
    def _formatContextualMemory(contextualMemory: dict[str, Any]) -> str:
        """Format contextual memory used to resolve follow-up references."""

        lines = [
            "Context for resolving references:",
            "- Use this context to resolve words like it, them, that, there, also, and too.",
            "- Prefer explicit user input over contextual memory when they conflict.",
            "- If context is insufficient, keep confidence below the threshold.",
        ]

        memory = contextualMemory.get("memory") or {}
        if memory:
            lines.append("Long-term memory:")
            for key, value in memory.items():
                lines.append(f"- {key}: {value}")

        recentToolContext = contextualMemory.get("recentToolContext") or []
        if recentToolContext:
            lines.append("Recent tool context:")
            for item in recentToolContext:
                lines.append(f"- {item}")

        runtimeState = contextualMemory.get("runtimeState") or {}
        if runtimeState:
            lines.append("Current runtime state:")
            for key, value in runtimeState.items():
                lines.append(f"- {key}: {value}")

        recentConversation = contextualMemory.get("recentConversation") or []
        if recentConversation:
            lines.append("Recent conversation summary:")
            for item in recentConversation:
                lines.append(f"- {item}")

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
            sections.append(f"Short-term conversation history:\n{historyText}")
        sections.append(f"User: {userPrompt}\nAura:")
        return "\n\n".join(section for section in sections if section)
