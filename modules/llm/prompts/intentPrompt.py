"""Structured intent parsing prompt profile."""


def buildIntentPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for deterministic structured intent parsing."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Interpret the user's request as structured JSON. "
        "Do not execute actions. Aura will validate and route the result."
    )

