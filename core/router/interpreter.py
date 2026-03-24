"""Convert raw input text into runtime intents."""

from core.router.intent import Intent


class Interpreter:
    """
    Convert raw user input into coarse runtime intents.

    Without a command layer, the interpreter focuses only on normal assistant
    intents and otherwise falls back to the LLM route.
    """

    def __init__(self, context):
        """Initialize the interpreter with runtime context and optional logging."""

        self.context = context
        self.logger = context.logger.getChild("Interpreter") if context.logger else None
        if self.logger:
            self.logger.info("Initialized.")

    def interpret(self, text: str):
        """
        Interpret raw user input and convert it into an Intent object.
        """

        if self.logger:
            self.logger.debug(f"Interpreting input: {text}")

        normalized = text.strip().lower()

        if "weather" in normalized:
            return Intent(name="weather", raw=text)
        if "remind" in normalized:
            return Intent(name="reminder", raw=text)
        if "time" in normalized:
            return Intent(name="time", raw=text)

        return Intent(name="llm", raw=text)
