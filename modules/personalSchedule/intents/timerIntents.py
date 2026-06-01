"""Timer intent descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


TIMER_INTENTS = (
    ModuleIntent(
        name="schedule.createTimer",
        description="Create a timer.",
        arguments={"durationSeconds": {"type": "integer"}},
        target="createTimer",
        requiredArguments=("durationSeconds",),
    ),
    ModuleIntent(
        name="schedule.completeTimer",
        description="Complete a timer.",
        arguments={"itemId": {"type": "string"}},
        target="completeTimer",
        requiredArguments=("itemId",),
    ),
)
