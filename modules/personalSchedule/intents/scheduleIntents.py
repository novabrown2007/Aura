"""Schedule intent descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


SCHEDULE_INTENTS = (
    ModuleIntent(
        name="schedule.createItem",
        description="Create a new schedule item from conversation.",
        arguments={"title": {"type": "string"}},
        target="createScheduleItem",
        requiredArguments=("title",),
    ),
    ModuleIntent(
        name="schedule.getToday",
        description="Ask for today's schedule.",
        arguments={},
        target="getTodaysSchedule",
    ),
)
