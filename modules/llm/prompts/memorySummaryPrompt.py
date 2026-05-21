"""Memory extraction prompt profile."""


def buildMemorySummaryPrompt(basePrompt: str, **_kwargs) -> str:
    """Return a prompt for extracting durable memory facts."""

    return (
        f"{basePrompt.strip()}\n\n"
        "Prompt mode: memory summarization.\n"
        "Extract durable user facts only.\n"
        "Ignore temporary commands, scheduling chatter, tool results, jokes, and guesses.\n"
        "Do not infer facts from implication. Only store facts explicitly stated by the user.\n"
        "Return structured JSON only, with stable snake_case keys and short string values."
    )

