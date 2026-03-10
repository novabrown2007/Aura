class LLMConfig:
    """
    Configuration for the Aura LLM system.
    """
    # Model configuration
    MODEL = "llama3.1:8b"
    ENDPOINT = "http://localhost:11434/api/generate"

    # Conversation history
    ENABLE_HISTORY = True
    HISTORY_LIMIT = 25

    # Long-term memory
    ENABLE_MEMORY = True
