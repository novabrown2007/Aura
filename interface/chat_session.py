"""Chat transcript and session handling for the Aura chat page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Thread
from uuid import uuid4


@dataclass
class ChatMessage:
    """One message in a conversation transcript."""

    message_id: str
    role: str
    text: str
    state: str = "done"
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatConversation:
    """One ChatGPT-style chat thread."""

    conversation_id: str
    title: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    messages: list[ChatMessage] = field(default_factory=list)
    scroll_offset: int = 0
    max_scroll: int = 0

    def append(self, role: str, text: str, state: str = "done", metadata: dict | None = None) -> ChatMessage:
        message = ChatMessage(
            message_id=uuid4().hex,
            role=str(role or "aura"),
            text=str(text or ""),
            state=str(state or "done"),
            metadata=dict(metadata or {}),
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow().isoformat(timespec="seconds")
        return message

    def last_user_text(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user" and message.text.strip():
                return message.text.strip()
        return ""

    def preview(self) -> str:
        for message in reversed(self.messages):
            text = str(message.text or "").strip()
            if text:
                return text
        return ""


class ChatSession:
    """Own the visible chat threads and background LLM execution."""

    def __init__(self, context=None, post_ui_event=None, thread_factory=None):
        self.context = context
        self.post_ui_event = post_ui_event
        self.thread_factory = thread_factory or Thread
        self.conversations: list[ChatConversation] = []
        self.active_conversation_id = ""
        self._storage_loaded = False
        self._load_from_storage()
        if not self.conversations:
            self.new_chat("New chat", persist=True)
        self._storage_loaded = True

    @property
    def messages(self) -> list[ChatMessage]:
        conversation = self.active_conversation
        return conversation.messages if conversation is not None else []

    @property
    def active_conversation(self) -> ChatConversation | None:
        for conversation in self.conversations:
            if conversation.conversation_id == self.active_conversation_id:
                return conversation
        return self.conversations[0] if self.conversations else None

    def set_context(self, context=None, post_ui_event=None):
        """Attach or replace the runtime context used for responses."""

        self.context = context
        if post_ui_event is not None:
            self.post_ui_event = post_ui_event
        if not self._storage_loaded:
            self.conversations.clear()
            self.active_conversation_id = ""
            self._load_from_storage()
            if not self.conversations:
                self.new_chat("New chat", persist=True)
            self._storage_loaded = True

    def list_conversations(self) -> list[dict]:
        """Return ChatGPT-style session summaries ordered by recency."""

        conversations = sorted(self.conversations, key=lambda item: item.updated_at, reverse=True)
        return [
            {
                "conversation_id": conversation.conversation_id,
                "title": conversation.title,
                "preview": conversation.preview(),
                "message_count": len(conversation.messages),
                "active": conversation.conversation_id == self.active_conversation_id,
                "updated_at": conversation.updated_at,
            }
            for conversation in conversations
        ]

    def memory_lines(self, limit: int = 3) -> list[str]:
        """Return a compact memory summary for the left rail."""

        conversation = self.active_conversation
        if conversation is None:
            return []

        lines: list[str] = []
        memory_manager = getattr(self.context, "memoryManager", None)
        if memory_manager is not None and hasattr(memory_manager, "getContext"):
            try:
                result = memory_manager.getContext(conversation.last_user_text(), conversationHistory=self._conversation_history_snapshot(conversation))
                memory_block = {}
                if isinstance(result, dict):
                    memory_block = dict(result.get("memory") or {})
                    if not memory_block:
                        memory_block = dict(result.get("contextualMemory") or {})
                for key, value in memory_block.items():
                    snippet = str(value or "").strip()
                    if not snippet:
                        continue
                    lines.append(f"{key}: {snippet}")
                    if len(lines) >= limit:
                        return lines[:limit]
            except Exception:
                pass

        return []

    def new_chat(self, title: str = "New chat", persist: bool = True) -> ChatConversation:
        """Create a blank chat tab and make it active."""

        conversation = ChatConversation(
            conversation_id=uuid4().hex,
            title=str(title or "New chat"),
        )
        self.conversations.insert(0, conversation)
        self.active_conversation_id = conversation.conversation_id
        if persist:
            self._persist_conversation(conversation)
        return conversation

    def switch_to(self, conversation_id: str) -> bool:
        """Activate an existing conversation tab."""

        if not conversation_id:
            return False
        for conversation in self.conversations:
            if conversation.conversation_id == conversation_id:
                self.active_conversation_id = conversation_id
                return True
        return False

    def delete_chat(self, conversation_id: str) -> bool:
        """Remove a chat tab and its persisted history."""

        if not conversation_id:
            return False

        conversation = self._conversation_by_id(conversation_id)
        if conversation is None:
            return False

        self._delete_persisted_conversation(conversation_id)
        self.conversations = [item for item in self.conversations if item.conversation_id != conversation_id]

        if not self.conversations:
            self.active_conversation_id = ""
            self.new_chat("New chat", persist=True)
            return True

        if self.active_conversation_id == conversation_id:
            self.active_conversation_id = self.conversations[0].conversation_id

        return True

    def scroll(self, delta: int, viewport_height: int) -> bool:
        """Scroll the active conversation transcript."""

        conversation = self.active_conversation
        if conversation is None:
            return False

        max_scroll = max(0, int(conversation.max_scroll))
        if max_scroll <= 0:
            conversation.scroll_offset = 0
            return False

        step = max(48, int(abs(delta) * 0.9))
        if delta > 0:
            conversation.scroll_offset = min(max_scroll, conversation.scroll_offset + step)
        else:
            conversation.scroll_offset = max(0, conversation.scroll_offset - step)
        return True

    def submit(self, prompt: str) -> bool:
        """Queue a prompt for LLM generation and add it to the active chat."""

        text = str(prompt or "").strip()
        if not text:
            return False

        conversation = self.active_conversation or self.new_chat()

        if conversation.title in {"New chat", "Current chat", "Conversation"} or not conversation.title.strip():
            conversation.title = self._title_from_prompt(text)
            self._persist_conversation(conversation)

        conversation.append("user", text)
        assistant_message = conversation.append(
            "aura",
            "Thinking...",
            state="pending",
            metadata={"requestId": uuid4().hex},
        )
        conversation.scroll_offset = 0
        self._touch_conversation(conversation)

        history_snapshot = self._conversation_history_snapshot(conversation)
        conversation_id = conversation.conversation_id

        def worker():
            try:
                response_text, backend = self._generate_response(text, history_snapshot, conversation_id)
                if backend == "llmManager":
                    self._record_history_turns(conversation_id, text, response_text)
                elif backend == "llm" and not getattr(getattr(self.context, "llm", None), "handlesConversationLogging", False):
                    self._record_history_turns(conversation_id, text, response_text)
                self._post_update(lambda: self._complete_request(conversation_id, assistant_message.message_id, response_text, None))
            except Exception as error:
                self._post_update(lambda: self._complete_request(conversation_id, assistant_message.message_id, "", error))

        thread = self.thread_factory(target=worker, daemon=True)
        thread.start()
        return True

    def _generate_response(self, prompt: str, conversation_history: list[tuple[str, str]], conversation_id: str):
        """Generate an assistant response using the configured backend."""

        context = self.context

        if context is not None and getattr(context, "llm", None) is not None and hasattr(context.llm, "generateResponse"):
            response = context.llm.generateResponse(prompt, conversationId=conversation_id)
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

    def _conversation_history_snapshot(self, conversation: ChatConversation) -> list[tuple[str, str]]:
        """Return the current completed transcript for fallback LLM calls."""

        snapshot: list[tuple[str, str]] = []
        for message in conversation.messages:
            if message.state == "pending":
                continue
            snapshot.append((message.role, message.text))
        return snapshot

    def _record_history_turns(self, conversation_id: str, user_text: str, assistant_text: str):
        """Persist a turn to the shared conversation history store."""

        history = getattr(self.context, "conversationHistory", None)
        if history is None or not hasattr(history, "logMessage"):
            return

        try:
            history.logMessage("user", user_text, conversationId=conversation_id)
            history.logMessage("aura", assistant_text, conversationId=conversation_id)
        except Exception:
            pass

    def _post_update(self, callback):
        """Schedule a transcript update back onto the Tk thread."""

        if self.post_ui_event is None:
            callback()
            return
        self.post_ui_event(callback)

    def _complete_request(self, conversation_id: str, assistant_message_id: str, response_text: str, error: Exception | None):
        """Replace the pending assistant bubble with the final response."""

        conversation = self._conversation_by_id(conversation_id)
        if conversation is None:
            return

        pending_index = None
        for index, message in enumerate(conversation.messages):
            if message.message_id == assistant_message_id:
                pending_index = index
                break

        if pending_index is None:
            return

        if error is not None:
            conversation.messages[pending_index] = ChatMessage(
                message_id=assistant_message_id,
                role="aura",
                text=f"I couldn't generate a response: {error}",
                state="error",
            )
            conversation.updated_at = datetime.utcnow().isoformat(timespec="seconds")
            return

        cleaned = str(response_text or "").strip() or "I don't have a response right now."
        conversation.messages[pending_index] = ChatMessage(
            message_id=assistant_message_id,
            role="aura",
            text=cleaned,
            state="done",
        )
        conversation.updated_at = datetime.utcnow().isoformat(timespec="seconds")
        self._touch_conversation(conversation)
        if conversation.conversation_id == self.active_conversation_id:
            conversation.scroll_offset = 0

    def _conversation_by_id(self, conversation_id: str) -> ChatConversation | None:
        for conversation in self.conversations:
            if conversation.conversation_id == conversation_id:
                return conversation
        return None

    def _load_from_storage(self):
        """Hydrate sessions and transcripts from persistent storage."""

        database = getattr(self.context, "database", None)
        history = getattr(self.context, "conversationHistory", None)
        if database is None:
            return

        loaded: dict[str, ChatConversation] = {}

        try:
            session_rows = database.fetchAll(
                """
                SELECT conversation_id, title, created_at, updated_at, last_message_at
                FROM chat_sessions
                ORDER BY COALESCE(last_message_at, updated_at, created_at) DESC
                """
            )
        except Exception:
            session_rows = []

        for row in session_rows or []:
            conversation_id = str(row.get("conversation_id") or "").strip()
            if not conversation_id:
                continue
            created_at = str(row.get("created_at") or datetime.utcnow().isoformat(timespec="seconds"))
            updated_at = str(row.get("updated_at") or datetime.utcnow().isoformat(timespec="seconds"))
            conversation = ChatConversation(
                conversation_id=conversation_id,
                title=str(row.get("title") or "New chat"),
                created_at=created_at,
                updated_at=updated_at,
            )
            loaded_messages: list[tuple[str, str]] = []
            if history is not None and hasattr(history, "getConversationMessages"):
                try:
                    loaded_messages = list(history.getConversationMessages(conversation_id))
                    for role, text in loaded_messages:
                        conversation.append(role, text)
                except Exception:
                    pass
            conversation.created_at = created_at
            conversation.updated_at = updated_at if loaded_messages else updated_at
            loaded[conversation_id] = conversation

        if history is not None and hasattr(history, "listConversationIds"):
            try:
                for conversation_id in history.listConversationIds():
                    if conversation_id in loaded:
                        continue
                    loaded_messages: list[tuple[str, str]] = []
                    try:
                        loaded_messages = list(history.getConversationMessages(conversation_id))
                    except Exception:
                        loaded_messages = []
                    conversation = ChatConversation(
                        conversation_id=conversation_id,
                        title=self._title_from_messages(loaded_messages),
                    )
                    for role, text in loaded_messages:
                        conversation.append(role, text)
                    loaded[conversation_id] = conversation
                    self._persist_conversation(conversation)
            except Exception:
                pass

        self.conversations = sorted(loaded.values(), key=lambda item: item.updated_at, reverse=True)
        if self.conversations and not self.active_conversation_id:
            self.active_conversation_id = self.conversations[0].conversation_id

    def _persist_conversation(self, conversation: ChatConversation):
        """Write chat metadata so tabs survive restarts."""

        database = getattr(self.context, "database", None)
        if database is None:
            return

        try:
            database.execute(
                """
                INSERT INTO chat_sessions (conversation_id, title, created_at, updated_at, last_message_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation.conversation_id,
                    conversation.title,
                    conversation.created_at,
                    conversation.updated_at,
                    conversation.updated_at,
                ),
            )
        except Exception:
            try:
                database.execute(
                    """
                    UPDATE chat_sessions
                    SET title = ?, updated_at = ?, last_message_at = ?
                    WHERE conversation_id = ?
                    """,
                    (
                        conversation.title,
                        conversation.updated_at,
                        conversation.updated_at,
                        conversation.conversation_id,
                    ),
                )
            except Exception:
                pass

    def _delete_persisted_conversation(self, conversation_id: str):
        """Remove stored chat metadata and conversation rows."""

        database = getattr(self.context, "database", None)
        if database is None:
            return

        history = getattr(self.context, "conversationHistory", None)
        if history is not None and hasattr(history, "clear"):
            try:
                history.clear(conversationId=conversation_id)
            except Exception:
                pass
        else:
            try:
                database.execute(
                    "DELETE FROM conversation_history WHERE conversation_id = ?",
                    (conversation_id,),
                )
            except Exception:
                pass

        try:
            database.execute(
                "DELETE FROM chat_sessions WHERE conversation_id = ?",
                (conversation_id,),
            )
        except Exception:
            pass

    def _touch_conversation(self, conversation: ChatConversation):
        """Refresh stored metadata after activity."""

        conversation.updated_at = datetime.utcnow().isoformat(timespec="seconds")
        self._persist_conversation(conversation)

    @staticmethod
    def _title_from_prompt(prompt: str) -> str:
        text = " ".join(str(prompt or "").split())
        if len(text) <= 28:
            return text or "Chat"
        return f"{text[:25].rstrip()}..."

    @staticmethod
    def _title_from_messages(messages: list[tuple[str, str]]) -> str:
        for role, text in messages:
            if role == "user" and str(text or "").strip():
                return ChatSession._title_from_prompt(text)
        return "New chat"
