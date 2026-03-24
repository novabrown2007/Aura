"""Event-related calendar commands for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import format_result, parse_key_value_args


class EventCreateCommand(BaseCommand):
    """Create a calendar event."""

    path = ("calendar", "event", "create")
    description = "Create an event. Usage: /calendar event create title=Meeting start_at='10:00 24/03/2026' [end_at='11:00 24/03/2026'] [description=...]"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "title" not in fields or "start_at" not in fields:
            return self.fail("Usage: /calendar event create title=Meeting start_at='10:00 24/03/2026' [end_at='11:00 24/03/2026']")
        event_id = self.context.require("calendar").createEvent(**fields)
        return self.ok(f"Created event {event_id}: {fields['title']}")


class EventGetCommand(BaseCommand):
    """Get one event by ID."""

    path = ("calendar", "event", "get")
    description = "Get one event. Usage: /calendar event get id=1"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar event get id=1")
        return self.ok(format_result(self.context.require("calendar").getEvent(int(fields["id"]))))


class EventListCommand(BaseCommand):
    """List or search events."""

    path = ("calendar", "event", "list")
    description = "List events. Usage: /calendar event list start_at='00:00 24/03/2026' end_at='23:59 24/03/2026' [calendar_id=1]"

    def execute(self, args):
        fields = parse_key_value_args(args)
        calendar = self.context.require("calendar")
        if "start_at" in fields and "end_at" in fields:
            rows = calendar.listEventsForRange(
                start_at=fields["start_at"],
                end_at=fields["end_at"],
                calendar_id=fields.get("calendar_id"),
            )
        else:
            rows = calendar.searchEvents(
                query=fields.get("query"),
                calendar_id=fields.get("calendar_id"),
                start_at=fields.get("start_at"),
                end_at=fields.get("end_at"),
                status=fields.get("status"),
                location=fields.get("location"),
                attendee=fields.get("attendee"),
                all_day=fields.get("all_day"),
            )
        return self.ok(format_result(rows))


class EventUpdateCommand(BaseCommand):
    """Update one event."""

    path = ("calendar", "event", "update")
    description = "Update an event. Usage: /calendar event update id=1 title='New title'"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar event update id=1 title='New title'")
        event_id = int(fields.pop("id"))
        self.context.require("calendar").updateEvent(event_id, **fields)
        return self.ok(f"Updated event {event_id}.")


class EventDeleteCommand(BaseCommand):
    """Delete one event."""

    path = ("calendar", "event", "delete")
    description = "Delete an event. Usage: /calendar event delete id=1"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar event delete id=1")
        event_id = int(fields["id"])
        self.context.require("calendar").deleteEvent(event_id)
        return self.ok(f"Deleted event {event_id}.")


class EventConflictsCommand(BaseCommand):
    """Detect overlapping events."""

    path = ("calendar", "event", "conflicts")
    description = "Show overlapping events. Usage: /calendar event conflicts start_at='10:00 24/03/2026' end_at='11:00 24/03/2026'"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "start_at" not in fields or "end_at" not in fields:
            return self.fail("Usage: /calendar event conflicts start_at='10:00 24/03/2026' end_at='11:00 24/03/2026'")
        rows = self.context.require("calendar").detectConflicts(
            start_at=fields["start_at"],
            end_at=fields["end_at"],
            calendar_id=fields.get("calendar_id"),
            exclude_event_id=fields.get("exclude_event_id"),
        )
        return self.ok(format_result(rows))


def build_commands(context):
    """Return event command objects for registry registration."""

    return [
        EventCreateCommand(context),
        EventGetCommand(context),
        EventListCommand(context),
        EventUpdateCommand(context),
        EventDeleteCommand(context),
        EventConflictsCommand(context),
    ]
