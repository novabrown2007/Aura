"""Chat transcript and session handling for the Aura chat page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Thread
from uuid import uuid4


@dataclass
class ChatMessage:
    """One message in the chat transcript."""

    message_id: str
    role: str
    text: str
    state: str = "done"
    metadata: dict = field(default_factory=dict)


class ChatSession:
    """Own the single visible chat transcript and background LLM execution."""

    def __init__(self, context=None, post_ui_event=None, thread_factory=None):
        self.context = context
        self.post_ui_event = post_ui_event
        self.thread_factory = thread_factory or Thread
        self.messages: list[ChatMessage] = []
        self.scroll_offset: int = 0
        self.max_scroll: int = 0

    def set_context(self, context=None, post_ui_event=None):
        """Attach or replace the runtime context used for responses."""

        self.context = context
        if post_ui_event is not None:
            self.post_ui_event = post_ui_event

    def submit(self, prompt: str) -> bool:
        """Queue a prompt for LLM generation and add it to the transcript."""

        text = str(prompt or "").strip()
        if not text:
            return False

        self.messages.append(
            ChatMessage(
                message_id=uuid4().hex,
                role="user",
                text=text,
            )
        )
        assistant_message = ChatMessage(
            message_id=uuid4().hex,
            role="aura",
            text="Thinking...",
            state="pending",
            metadata={"requestId": uuid4().hex},
        )
        self.messages.append(assistant_message)
        self.scroll_offset = 0

        history_snapshot = self._conversation_history_snapshot()

        def worker():
            try:
                response_text, backend = self._generate_response(text, history_snapshot)
                if backend == "llmManager":
                    self._record_history_turns(text, response_text)
                self._post_update(lambda: self._complete_request(assistant_message.message_id, response_text, None))
            except Exception as error:
                self._post_update(lambda: self._complete_request(assistant_message.message_id, "", error))

        thread = self.thread_factory(target=worker, daemon=True)
        thread.start()
        return True

    def scroll(self, delta: int, viewport_height: int) -> bool:
        """Scroll the transcript."""

        max_scroll = max(0, int(self.max_scroll))
        if max_scroll <= 0:
            self.scroll_offset = 0
            return False

        step = max(48, int(abs(delta) * 0.9))
        if delta > 0:
            self.scroll_offset = min(max_scroll, self.scroll_offset + step)
        else:
            self.scroll_offset = max(0, self.scroll_offset - step)
        return True

    def _generate_response(self, prompt: str, conversation_history: list[tuple[str, str]]):
        """Generate an assistant response using the configured backend."""

        context = self.context

        if context is not None and getattr(context, "llm", None) is not None and hasattr(context.llm, "generateResponse"):
            response = context.llm.generateResponse(prompt)
            return str(response or ""), "llm"

        if context is not None and getattr(context, "llmManager", None) is not None:
            system_prompt = (
                "You are Aura, a private AI assistant for Nova. "
                "Respond as Aura only. Keep replies concise, clear, and helpful."
            )
            response = context.llmManager.generateResponse(system_prompt, prompt, conversation_history)
            if getattr(response, "success", False):
                return str(response.asText("") or response.text or ""), "llmManager"
            return str(response.error or "I could not generate a response right now."), "llmManager"

        return "LLM functionality is not available in this window.", "none"

    def _conversation_history_snapshot(self) -> list[tuple[str, str]]:
        """Return the current completed transcript for fallback LLM calls."""

        snapshot: list[tuple[str, str]] = []
        for message in self.messages:
            if message.state == "pending":
                continue
            snapshot.append((message.role, message.text))
        return snapshot

    def _record_history_turns(self, user_text: str, assistant_text: str):
        """Persist a turn to the shared conversation history store."""

        history = getattr(self.context, "conversationHistory", None)
        if history is None or not hasattr(history, "logMessage"):
            return

        try:
            history.logMessage("user", user_text)
            history.logMessage("aura", assistant_text)
        except Exception:
            pass

    def _post_update(self, callback):
        """Schedule a transcript update back onto the Tk thread."""

        if self.post_ui_event is None:
            callback()
            return
        self.post_ui_event(callback)

    def _complete_request(self, assistant_message_id: str, response_text: str, error: Exception | None):
        """Replace the pending assistant bubble with the final response."""

        pending_index = None
        for index, message in enumerate(self.messages):
            if message.message_id == assistant_message_id:
                pending_index = index
                break

        if pending_index is None:
            return

        if error is not None:
            self.messages[pending_index] = ChatMessage(
                message_id=assistant_message_id,
                role="aura",
                text=f"I couldn't generate a response: {error}",
                state="error",
            )
            return

        cleaned = str(response_text or "").strip() or "I don't have a response right now."
        self.messages[pending_index] = ChatMessage(
            message_id=assistant_message_id,
            role="aura",
            text=cleaned,
            state="done",
        )
        self.scroll_offset = 0

