"""
Aura Assistant
LLM Handler Module

Handles communication between Aura and the local language model
runtime powered by Ollama.

Responsibilities:
- Construct prompts using long-term memory and recent conversation
- Send prompts to the language model
- Return generated responses
"""

import requests


class LLMHandler:
    """
    Handles interaction with the local language model.
    """

    def __init__(self, context):
        """
        Initialize the LLM handler.

        Args
        ----
        context : RuntimeContext
            Global runtime context.
        """

        self.context = context
        self.logger = context.logger.logger.getChild("LLM") if context.logger else None

        # Ollama API endpoint
        self.endpoint = "http://localhost:11434/api/generate"

        # Model used for inference
        self.model = "llama3.1:8b"

        # Managers
        self.history = context.conversationHistory
        self.memory = context.memoryManager

        if self.logger:
            self.logger.info("Initialized")

    # --------------------------------------------------
    # Response Generation
    # --------------------------------------------------

    def generateResponse(self, userInput: str) -> str:
        """
        Generate a response from the language model.
        """

        try:

            # --------------------------------
            # Long-term memory
            # --------------------------------

            memoryData = self.memory.getMemory()

            memorySection = ""

            for key, value in memoryData.items():
                memorySection += f"{key}: {value}\n"

            # --------------------------------
            # Conversation history
            # --------------------------------

            messages = self.history.getRecentMessages(limit=15)

            # --------------------------------
            # System prompt
            # --------------------------------

            systemPrompt = f"""
You are Aura, a helpful personal assistant similar to Jarvis.

Rules:
- Respond as Aura only.
- Do not speak for the user.
- Do not repeat messages unless necessary.
- Keep responses concise and helpful.
- Never claim to access system logs or internal program state unless explicitly provided.

Important long-term memory:
{memorySection}
"""

            # --------------------------------
            # Build conversation
            # --------------------------------

            conversation = systemPrompt.strip() + "\n\nConversation history:\n\n"

            for author, content in messages:

                if author == "user":
                    conversation += f"User: {content}\n"

                elif author == "aura":
                    conversation += f"Aura: {content}\n"

            # Add latest user input
            conversation += f"\nUser: {userInput}\nAura:"

            # --------------------------------
            # Send request
            # --------------------------------

            payload = {
                "model": self.model,
                "prompt": conversation,
                "stream": False
            }

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
                return "I don't have a response for that."

            return cleaned

        except Exception as error:

            if self.logger:
                self.logger.error(f"LLM communication error: {error}")

            return "I am currently unable to access my language model."
