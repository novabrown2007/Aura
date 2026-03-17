"""
Aura Assistant
LLM Handler Module

Handles communication between Aura and the local language model
runtime powered by Ollama.

Responsibilities
----------------
- Construct prompts using conversation history and long-term memory
- Send prompts to the language model
- Receive generated responses
- Log conversation messages
- Respect runtime configuration settings
"""

import requests


class LLMHandler:
    """
    Handles interaction with the local language model.

    This class is responsible for building prompts, calling the LLM
    API, and returning the generated responses.
    """

    def __init__(self, context):
        """
        Initialize the LLM handler.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        # Logger
        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("LLM")
        # Configuration
        config = context.config
        # Required configuration values
        self.endpoint = config.require("llm.endpoint")
        self.model = config.require("llm.model")
        # Optional configuration
        self.history_enabled = config.get("llm.history.enabled", True)
        self.history_limit = config.get("llm.history.limit", 25)
        self.memory_enabled = config.get("llm.memory.enabled", True)
        # Managers
        self.history = context.conversationHistory
        self.memory = context.memoryManager
        if self.logger:
            self.logger.info("Initialized.")


    # --------------------------------------------------
    # Prompt Construction
    # --------------------------------------------------
    def _buildPrompt(self, userInput: str) -> str:
        """
        Construct the prompt sent to the language model.

        Args:
            userInput (str):
                Latest user message.

        Returns:
            str:
                Complete prompt string.
        """


        # --------------------------------
        # Long-term memory
        # --------------------------------
        memorySection = ""
        if self.memory_enabled and self.memory:
            memoryData = self.memory.getMemory()
            if memoryData:
                memorySection += "Known user information:\n"
                for key, value in memoryData.items():
                    memorySection += f"- {key}: {value}\n"
            else:
                memorySection = "No stored user information."


        # --------------------------------
        # Conversation history
        # --------------------------------
        messages = []
        if self.history_enabled:
            messages = self.history.getRecentMessages(limit=self.history_limit)


        # --------------------------------
        # System prompt
        # --------------------------------
        systemPrompt = f"""
You are Aura, a helpful personal assistant similar to Jarvis.

Rules:
- Respond as Aura only.
- Do not speak for the user.
- Keep responses concise and helpful.
- Do not claim to access internal system data unless explicitly provided.

{memorySection}
"""


        # --------------------------------
        # Build conversation section
        # --------------------------------

        conversation = systemPrompt.strip()

        if messages:
            conversation += "\n\nPrevious conversation:\n\n"
            for role, content in messages:
                if role == "user":
                    conversation += f"User: {content}\n"
                elif role == "aura":
                    conversation += f"Aura: {content}\n"

        # Append latest user input
        conversation += f"\nUser: {userInput}\nAura:"

        return conversation


    # --------------------------------------------------
    # Response Generation
    # --------------------------------------------------
    def generateResponse(self, userInput: str) -> str:
        """
        Generate a response from the language model.

        Args:
            userInput (str):
                User input message.

        Returns:
            str:
                Generated assistant response.
        """

        try:
            # --------------------------------
            # Learn long-term memory
            # --------------------------------
            if self.memory_enabled and self.memory:
                try:
                    self.memory.learnFromMessage(userInput)
                except Exception as memoryError:
                    if self.logger:
                        self.logger.warning(
                            f"Memory extraction failed: {memoryError}"
                        )


            # --------------------------------
            # Build prompt
            # --------------------------------
            prompt = self._buildPrompt(userInput)
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }


            # --------------------------------
            # Send request to LLM
            # --------------------------------
            response = requests.post(self.endpoint, json=payload)
            if response.status_code != 200:
                if self.logger:
                    self.logger.error(f"Ollama API error: {response.text}")
                return "I encountered an issue contacting my language model."

            data = response.json()
            modelResponse = data.get("response")
            if modelResponse is None:
                if self.logger:
                    self.logger.error(f"Unexpected Ollama response: {data}")
                return "I couldn't generate a response."

            cleaned = modelResponse.strip()
            if cleaned == "":
                cleaned = "I don't have a response for that."


            # --------------------------------
            # Log conversation
            # --------------------------------

            try:
                if self.history:
                    self.history.logMessage("user", userInput)
                    self.history.logMessage("aura", cleaned)

            except Exception as historyError:
                if self.logger:
                    self.logger.warning(
                        f"Conversation logging failed: {historyError}"
                    )

            return cleaned

        except Exception as error:
            if self.logger:
                self.logger.error(f"LLM communication error: {error}")
            return "I am currently unable to access my language model."
