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
            self.logger.info("Interpreter initialized.")

    def interpret(self, text: str):
        """
        Interpret raw user input and convert it into an Intent object.
        """

        if self.logger:
            self.logger.debug(f"Interpreting input: {text}")

        normalized = text.strip().lower()

        if "weather" in normalized:
            intent_name = "weather.current"
            if any(term in normalized for term in ("forecast", "tomorrow", "today", "week", "hour", "rain", "snow", "will it", "chance")):
                intent_name = "weather.forecast"
            if any(term in normalized for term in ("alert", "warning", "storm", "severe", "tornado", "flood", "heat", "cold")):
                intent_name = "weather.alerts"
            return Intent(name=intent_name, raw=text, data={"location": self._extractLocation(text)})
        if "remind" in normalized:
            return Intent(name="reminder", raw=text)
        if "time" in normalized:
            return Intent(name="time", raw=text)

        return Intent(name="llm", raw=text)

    @staticmethod
    def _extractLocation(text: str) -> str:
        lowered = str(text or "").strip()
        for marker in (" in ", " for ", " at ", " near "):
            if marker in lowered.lower():
                tail = lowered.lower().split(marker, 1)[1].strip(" ?.!")
                return tail.title() if tail else ""
        return ""
