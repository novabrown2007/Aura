"""Reusable prompt profiles for Aura cognition tasks."""

from modules.llm.prompts.automationPrompt import buildAutomationPrompt
from modules.llm.prompts.conversationPrompt import buildConversationPrompt
from modules.llm.prompts.intentPrompt import buildIntentPrompt
from modules.llm.prompts.memorySummaryPrompt import buildMemorySummaryPrompt
from modules.llm.prompts.toolSelectionPrompt import buildToolSelectionPrompt

PROMPT_PROFILES = {
    "conversation": buildConversationPrompt,
    "intentParsing": buildIntentPrompt,
    "toolSelection": buildToolSelectionPrompt,
    "memorySummary": buildMemorySummaryPrompt,
    "automation": buildAutomationPrompt,
}

__all__ = ["PROMPT_PROFILES"]

