"""Timer action descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


TIMER_ACTIONS = (
    ModuleAction(
        name="schedule.createTimer",
        description="Create a timer schedule item.",
        method="createTimer",
        parameters={"title": {"type": "string"}, "durationSeconds": {"type": "integer"}},
        requiredParameters=("durationSeconds",),
        capabilities=("schedule.timers",),
    ),
    ModuleAction(
        name="schedule.pauseTimer",
        description="Pause an active timer.",
        method="pauseTimer",
        parameters={"itemId": {"type": "string"}},
        requiredParameters=("itemId",),
        capabilities=("schedule.timers",),
    ),
    ModuleAction(
        name="schedule.resumeTimer",
        description="Resume a paused timer.",
        method="resumeTimer",
        parameters={"itemId": {"type": "string"}},
        requiredParameters=("itemId",),
        capabilities=("schedule.timers",),
    ),
    ModuleAction(
        name="schedule.completeTimer",
        description="Mark a timer as completed.",
        method="completeTimer",
        parameters={"itemId": {"type": "string"}},
        requiredParameters=("itemId",),
        capabilities=("schedule.timers",),
    ),
)
