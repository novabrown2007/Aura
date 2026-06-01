"""Schedule action descriptors for Aura's personal schedule hub."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


SCHEDULE_ACTIONS = (
    ModuleAction(
        name="schedule.createItem",
        description="Create a unified schedule item.",
        method="createScheduleItem",
        parameters={
            "title": {"type": "string"},
            "description": {"type": "string"},
            "type": {"type": "string"},
            "startTime": {"type": "string"},
            "endTime": {"type": "string"},
            "dueTime": {"type": "string"},
            "priority": {"type": "string"},
        },
        requiredParameters=("title",),
        capabilities=("schedule.write",),
    ),
    ModuleAction(
        name="schedule.updateItem",
        description="Update a unified schedule item.",
        method="updateScheduleItem",
        parameters={"itemId": {"type": "string"}},
        requiredParameters=("itemId",),
        capabilities=("schedule.modify",),
    ),
    ModuleAction(
        name="schedule.deleteItem",
        description="Delete a unified schedule item.",
        method="deleteScheduleItem",
        parameters={"itemId": {"type": "string"}},
        requiredParameters=("itemId",),
        capabilities=("schedule.modify",),
    ),
    ModuleAction(
        name="schedule.getToday",
        description="Return today's unified schedule summary.",
        method="getTodaysSchedule",
        capabilities=("schedule.read",),
    ),
    ModuleAction(
        name="schedule.getUpcoming",
        description="Return upcoming schedule items.",
        method="getUpcomingSchedule",
        parameters={"limit": {"type": "integer"}},
        capabilities=("schedule.read",),
    ),
)
