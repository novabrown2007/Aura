"""Tool selection prompt profile."""


def buildToolSelectionPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for selecting deterministic Aura tools."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Prompt mode: tool selection.\n"
        "Select deterministic Aura tools only when a module should perform an action.\n"
        "Return JSON with response and toolCalls only.\n"
        "Use exact registered tool names and arguments.\n"
        "Do not invent tools, execute tools, or claim execution."
    )

