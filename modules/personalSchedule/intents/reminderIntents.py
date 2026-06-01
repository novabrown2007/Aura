"""Reminder intent descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


REMINDER_INTENTS = (
    ModuleIntent(
        name="schedule.createReminder",
        description="Create a reminder.",
        arguments={"title": {"type": "string"}, "dueTime": {"type": "string"}},
        target="createReminder",
        requiredArguments=("title", "dueTime"),
    ),
)
