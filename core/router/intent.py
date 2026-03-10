class Intent:
    """
    Represents a structured user intent.

    An Intent is produced by the Interpreter and consumed by the
    IntentRouter. It contains the detected intent name along with
    the original user input and any parsed data extracted from it.
    """

    def __init__(self, name: str, raw: str, data=None):
        """
        Initialize an Intent.

        Args:
            name (str):
                Name of the detected intent.

            raw (str):
                The original user input.

            data (dict | None):
                Optional structured data extracted from the input.
        """

        self.name = name
        """The detected intent name."""

        self.raw = raw
        """The original user message."""

        self.data = data or {}
        """Optional structured data extracted by the interpreter."""

    # --------------------------------------------------
    # Debug Helpers
    # --------------------------------------------------

    def __repr__(self):
        """
        Return a developer-friendly representation of the intent.
        """

        return f"Intent(name={self.name}, data={self.data})"
