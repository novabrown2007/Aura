"""Task intent descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


TASK_INTENTS = (
    ModuleIntent(
        name="schedule.createTask",
        description="Create a task.",
        arguments={"title": {"type": "string"}},
        target="createTask",
        requiredArguments=("title",),
    ),
    ModuleIntent(
        name="schedule.completeTask",
        description="Complete a task.",
        arguments={"itemId": {"type": "string"}},
        target="completeTask",
        requiredArguments=("itemId",),
    ),
)
