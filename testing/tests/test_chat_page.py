"""Tests for the Aura chat page transcript and prompt flow."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from interface.pages.chat_page import ChatPage
from modules.llm.conversationHistory import ConversationHistory
from testing.tests.support.fakes import InMemoryDatabase, make_context


class ImmediateThread:
    """Run threaded work immediately for deterministic tests."""

    def __init__(self, target=None, daemon=None):
        self.target = target

    def start(self):
        if self.target is not None:
            self.target()


class ChatPageTests(unittest.TestCase):
    """Chat page behavior testing.tests."""

    def test_submit_prompt_appends_user_and_assistant_messages(self):
        context = SimpleNamespace(
            llm=SimpleNamespace(generateResponse=lambda prompt, conversationId="": f"Response: {prompt}"),
            llmManager=None,
            conversationHistory=None,
        )
        page = ChatPage(context=context, thread_factory=ImmediateThread)

        submitted = page.submit_prompt("Hello Aura")

        self.assertTrue(submitted)
        self.assertEqual(len(page.session.messages), 2)
        self.assertEqual(page.session.messages[0].role, "user")
        self.assertEqual(page.session.messages[0].text, "Hello Aura")
        self.assertEqual(page.session.messages[1].role, "aura")
        self.assertEqual(page.session.messages[1].text, "Response: Hello Aura")
        self.assertEqual(page.session.messages[1].state, "done")

    def test_new_chat_starts_blank_and_does_not_reuse_seed_history(self):
        context = SimpleNamespace(
            llm=None,
            llmManager=None,
            conversationHistory=SimpleNamespace(getRecentMessages=lambda limit=20: [("user", "Seed"), ("aura", "Seed reply")]),
        )
        page = ChatPage(context=context, thread_factory=ImmediateThread)

        page.session.new_chat()

        self.assertEqual(page.session.messages, [])
        self.assertEqual(page.session.list_conversations()[0]["title"], "New chat")
        self.assertNotEqual(page.session.list_conversations()[0]["conversation_id"], "")

    def test_scroll_updates_active_conversation_offset(self):
        page = ChatPage(context=SimpleNamespace(llm=None, llmManager=None, conversationHistory=None), thread_factory=ImmediateThread)
        conversation = page.session.active_conversation
        self.assertIsNotNone(conversation)
        conversation.max_scroll = 240

        scrolled = page.session.scroll(120, 500)

        self.assertTrue(scrolled)
        self.assertGreater(conversation.scroll_offset, 0)

    def test_chat_sessions_persist_across_restarts(self):
        database = InMemoryDatabase()

        context = make_context(database=database)
        context.conversationHistory = ConversationHistory(context)
        context.llm = SimpleNamespace(
            generateResponse=lambda prompt, conversationId="": f"Response: {prompt}"
        )

        page = ChatPage(context=context, thread_factory=ImmediateThread)
        page.session.new_chat("Scratchpad")
        page.session.new_chat("Working chat")
        page.submit_prompt("Remember this chat")

        restarted_context = make_context(database=database)
        restarted_context.conversationHistory = ConversationHistory(restarted_context)
        restarted_context.llm = SimpleNamespace(
            generateResponse=lambda prompt, conversationId="": f"Response: {prompt}"
        )

        restarted = ChatPage(context=restarted_context, thread_factory=ImmediateThread)
        conversations = restarted.session.list_conversations()
        titles = [conversation["title"] for conversation in conversations]

        self.assertIn("Scratchpad", titles)
        self.assertIn("Working chat", titles)
        restored = next(conversation for conversation in conversations if conversation["title"] == "Working chat")
        self.assertGreaterEqual(restored["message_count"], 2)

    def test_delete_chat_removes_it_from_sidebar_and_storage(self):
        database = InMemoryDatabase()
        context = make_context(database=database)
        context.conversationHistory = ConversationHistory(context)
        context.llm = SimpleNamespace(generateResponse=lambda prompt, conversationId="": f"Response: {prompt}")

        page = ChatPage(context=context, thread_factory=ImmediateThread)
        deleted = page.session.new_chat("Disposable")
        page.session.new_chat("Keep me")

        self.assertTrue(page.session.delete_chat(deleted.conversation_id))
        titles = [conversation["title"] for conversation in page.session.list_conversations()]
        self.assertNotIn("Disposable", titles)

        restarted_context = make_context(database=database)
        restarted_context.conversationHistory = ConversationHistory(restarted_context)
        restarted_context.llm = SimpleNamespace(generateResponse=lambda prompt, conversationId="": f"Response: {prompt}")
        restarted = ChatPage(context=restarted_context, thread_factory=ImmediateThread)

        restarted_titles = [conversation["title"] for conversation in restarted.session.list_conversations()]
        self.assertNotIn("Disposable", restarted_titles)
        self.assertIn("Keep me", restarted_titles)


if __name__ == "__main__":
    unittest.main()
