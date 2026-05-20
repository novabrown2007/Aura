"""Automation planning prompt profile."""


def buildAutomationPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for automation planning without direct execution."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Plan automation through deterministic Aura tools. Never execute or simulate execution in text."
    )

