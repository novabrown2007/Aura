"""Prompt-safe memory injection for Aura prompts."""

from __future__ import annotations


class PromptInjector:
    """Append concise memory context without polluting user or tool sections."""

    def __init__(self, formatter, context=None):
        self.formatter = formatter
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.PromptInjector") if logger else None

    def inject(self, systemPrompt: str, memorySection: str) -> str:
        """Inject a rendered memory section into a system prompt."""

        prompt = str(systemPrompt or "").rstrip()
        section = str(memorySection or "").strip()
        if not section:
            return prompt
        if self.logger:
            self.logger.info("Injected tuned memory context into system prompt")
        return f"{prompt}\n\n{section}"

    def renderAndInject(self, systemPrompt: str, lines: list[str]) -> str:
        """Render memory lines and inject them."""

        return self.inject(systemPrompt, self.formatter.formatSection(lines))

