"""Tests for the Aura chat page transcript and prompt flow."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from interface.pages.chat_page import ChatPage


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
            llm=SimpleNamespace(generateResponse=lambda prompt: f"Response: {prompt}"),
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

    def test_scroll_updates_transcript_offset(self):
        page = ChatPage(context=SimpleNamespace(llm=None, llmManager=None, conversationHistory=None), thread_factory=ImmediateThread)
        page.session.max_scroll = 240

        scrolled = page.session.scroll(120, 500)

        self.assertTrue(scrolled)
        self.assertGreater(page.session.scroll_offset, 0)


if __name__ == "__main__":
    unittest.main()
