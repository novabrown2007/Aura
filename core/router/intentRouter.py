"""Intent routing for Aura's headless runtime."""


class IntentRouter:
    """
    Route interpreted intents to modules or fall back to the LLM.
    """

    def __init__(self, context):
        """Initialize the intent router."""

        self.context = context
        self.logger = context.logger.getChild("Router") if context.logger else None
        if self.logger:
            self.logger.info("Intent router initialized.")

    def route(self, intent):
        """
        Route an intent to the correct module or to the LLM fallback.
        """

        intent_name = intent.name
        if self.logger:
            self.logger.debug(f"Routing intent: {intent_name}")

        for module in self.context.modules.values():
            if hasattr(module, "canHandle") and module.canHandle(intent):
                if self.logger:
                    self.logger.debug(
                        f"Intent '{intent_name}' handled by {module.__class__.__name__}"
                    )
                response = module.handle(intent)
                self._speakResponse(response)
                return response

        if self.logger:
            self.logger.debug(
                f"No module handled intent '{intent_name}', using LLM fallback"
            )
        llm = self.context.require("llm")
        return llm.generateResponse(intent.raw)

    def _speakResponse(self, response):
        """Send module-generated text through shared voice playback when available."""

        if not isinstance(response, str):
            return

        voice = getattr(self.context, "voiceManager", None)
        if voice is None or not getattr(voice, "outputEnabled", False):
            return

        try:
            voice.speakResponse(response)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice playback failed for routed intent: {error}")
