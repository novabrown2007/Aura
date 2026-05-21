"""Structured intent parsing prompt profile."""


def buildIntentPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for deterministic structured intent parsing."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Prompt mode: intent parsing.\n"
        "Classify the user's request into ordered Aura intents only.\n"
        "Resolve references using supplied context, but do not invent missing facts.\n"
        "Return structured JSON only. Do not answer conversationally.\n"
        "Do not execute actions. Aura will validate and route the result."
    )

