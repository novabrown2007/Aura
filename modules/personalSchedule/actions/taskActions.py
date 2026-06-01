"""Task action descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


TASK_ACTIONS = (
    ModuleAction(
        name="schedule.createTask",
        description="Create a task schedule item.",
        method="createTask",
        parameters={"title": {"type": "string"}, "dueDate": {"type": "string"}},
        requiredParameters=("title",),
        capabilities=("schedule.tasks",),
    ),
    ModuleAction(
        name="schedule.completeTask",
        description="Mark a task as completed.",
        method="completeTask",
        parameters={"itemId": {"type": "string"}},
        requiredParameters=("itemId",),
        capabilities=("schedule.modify",),
    ),
)
