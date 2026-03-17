from core.router.intent import Intent


class Interpreter:
    """
    Converts raw user input into structured Intent objects.

    The Interpreter is responsible for analyzing user text and
    determining the most likely intent. For now this uses simple
    rule-based detection, but it can later be expanded to use
    LLM classification or machine learning models.
    """

    def __init__(self, context):
        """
        Initialize the interpreter.

        Args:
            context (RuntimeContext)
        """

        self.context = context
        self.logger = context.logger.getChild("Interpreter") if context.logger else None

        if self.logger:
            self.logger.info("Initialized.")

    # --------------------------------------------------
    # Interpretation
    # --------------------------------------------------

    def interpret(self, text: str):
        """
        Interpret raw user input and convert it into an Intent.

        Args:
            text (str)

        Returns:
            Intent
        """

        if self.logger:
            self.logger.debug(f"Interpreting input: {text}")

        normalized = text.lower().strip()

        # --------------------------------------------------
        # Simple Rule-Based Intents
        # --------------------------------------------------

        if "weather" in normalized:
            return Intent(
                name="weather",
                raw=text
            )

        if "remind" in normalized:
            return Intent(
                name="reminder",
                raw=text
            )

        if "time" in normalized:
            return Intent(
                name="time",
                raw=text
            )

        # --------------------------------------------------
        # Default Intent (LLM)
        # --------------------------------------------------

        return Intent(
            name="llm",
            raw=text
        )
