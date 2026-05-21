"""Automation planning prompt profile."""


def buildAutomationPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for automation planning without direct execution."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Prompt mode: automation planning.\n"
        "Convert goals into a cautious automation plan before any execution.\n"
        "Prefer event-driven steps, explicit triggers, conditions, and rollback notes.\n"
        "Identify required tools by name, but do not call them.\n"
        "Never execute, simulate execution, or claim that an automation has been installed."
    )

