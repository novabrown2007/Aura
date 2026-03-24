"""Calendar command registration for Aura CLI."""

from modules.commands.calendarCommands.calendarCreateCommand import CalendarCreateCommand
from modules.commands.calendarCommands.calendarDayCommand import CalendarDayCommand
from modules.commands.calendarCommands.calendarListCommand import CalendarListCommand
from modules.commands.calendarCommands.calendarMonthCommand import CalendarMonthCommand
from modules.commands.calendarCommands.calendarWeekCommand import CalendarWeekCommand
from modules.commands.calendarCommands.eventCommands import build_commands as build_event_commands
from modules.commands.calendarCommands.taskCommands import build_commands as build_task_commands
from modules.commands.calendarCommands.reminderCommands import build_commands as build_reminder_commands


def build_commands(context):
    """Return the calendar command objects for registry registration."""

    return [
        CalendarListCommand(context),
        CalendarCreateCommand(context),
        CalendarDayCommand(context),
        CalendarWeekCommand(context),
        CalendarMonthCommand(context),
        *build_event_commands(context),
        *build_task_commands(context),
        *build_reminder_commands(context),
    ]
