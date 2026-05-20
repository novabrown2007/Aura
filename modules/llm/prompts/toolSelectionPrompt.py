"""Tool selection prompt profile."""


def buildToolSelectionPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for selecting deterministic Aura tools."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Select tools only when a deterministic Aura module should perform an action. "
        "Return JSON with response and toolCalls. Do not claim execution."
    )

