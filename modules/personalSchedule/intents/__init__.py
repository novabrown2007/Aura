"""Intent descriptors for Aura's personal schedule hub."""

from modules.personalSchedule.intents.reminderIntents import REMINDER_INTENTS
from modules.personalSchedule.intents.scheduleIntents import SCHEDULE_INTENTS
from modules.personalSchedule.intents.taskIntents import TASK_INTENTS
from modules.personalSchedule.intents.timerIntents import TIMER_INTENTS

__all__ = ["REMINDER_INTENTS", "SCHEDULE_INTENTS", "TASK_INTENTS", "TIMER_INTENTS"]
