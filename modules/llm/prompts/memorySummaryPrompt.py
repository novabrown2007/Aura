"""Memory extraction prompt profile."""


def buildMemorySummaryPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for extracting durable memory facts."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Extract durable user facts only. Ignore temporary commands, scheduling chatter, and guesses."
    )

