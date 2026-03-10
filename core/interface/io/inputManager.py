class InputManager:
    """
    Handles incoming user input for Aura.

    The InputManager receives raw input from interfaces (CLI, web,
    mobile, speech, etc.) and passes it through the interpreter and
    router to generate a response.
    """

    def __init__(self, context):
        """
        Initialize the InputManager.

        Args:
            context (RuntimeContext)
        """

        self.context = context
        self.logger = context.logger.getChild("Input") if context.logger else None

        if self.logger:
            self.logger.info("Initialized")

    # --------------------------------------------------
    # Input Processing
    # --------------------------------------------------

    def process(self, text: str):
        """
        Process incoming user input.

        Args:
            text (str)

        Returns:
            str:
                The assistant response.
        """

        if self.logger:
            self.logger.debug(f"Received input: {text}")

        interpreter = self.context.require("interpreter")
        router = self.context.require("intentRouter")

        # Convert text → intent
        intent = interpreter.interpret(text)

        # Route intent → module/LLM
        response = router.route(intent)

        return response
