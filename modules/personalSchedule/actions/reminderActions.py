"""Reminder action descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


REMINDER_ACTIONS = (
    ModuleAction(
        name="schedule.createReminder",
        description="Create a reminder schedule item.",
        method="createReminder",
        parameters={"title": {"type": "string"}, "dueTime": {"type": "string"}},
        requiredParameters=("title", "dueTime"),
        capabilities=("schedule.reminders",),
    ),
)
