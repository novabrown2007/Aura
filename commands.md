# Aura CLI Commands

This document explains the purpose and usage of every registered slash command in the `interface/CLI` branch.

## How the CLI works

- Any input that starts with `/` is treated as a command.
- Any input that does **not** start with `/` is treated as normal chat and routed through Aura's standard input flow.
- Some commands use positional arguments.
- Some commands use `key=value` arguments.
- If a value contains spaces, wrap it in quotes.

Examples:

```text
/status
/memory set project Aura
/config get llm.model
/calendar event create title="Meeting" start_at="10:00 24/03/2026"
/reminder create title="Take meds" content="After dinner" module=system remind_at="19:00 24/03/2026"
```

---

## General commands

### `/help`
**Purpose:** Show every registered CLI command and its one-line description.

**Usage:**
```text
/help
```

### `/status`
**Purpose:** Show a high-level runtime summary, including loaded modules, scheduler state, database connection state, and restart status.

**Usage:**
```text
/status
```

### `/version`
**Purpose:** Show the current CLI branch/runtime version string.

**Usage:**
```text
/version
```

---

## Config commands

### `/config get <key>`
**Purpose:** Read a config value using dot notation.

**Usage:**
```text
/config get llm.model
/config get database.host
```

### `/config reload`
**Purpose:** Reload configuration from disk.

**Usage:**
```text
/config reload
```

### `/config set <key> <value>`
**Purpose:** Update a config value in `config.yml` and reload it in memory.

**Usage:**
```text
/config set llm.model llama3.1:8b
/config set database.port 3306
/config set llm.history.limit 15
```

### `/config validate`
**Purpose:** Check whether required config keys are present.

**Usage:**
```text
/config validate
```

---

## History commands

### `/history show [limit]`
**Purpose:** Show recent conversation history.

**Usage:**
```text
/history show
/history show 10
```

### `/history clear`
**Purpose:** Clear stored conversation history.

**Usage:**
```text
/history clear
```

---

## Memory commands

### `/memory get <key>`
**Purpose:** Read one stored memory entry.

**Usage:**
```text
/memory get project
```

### `/memory set <key> <value>`
**Purpose:** Store one memory entry.

**Usage:**
```text
/memory set project Aura
/memory set user_name Nova
```

### `/memory remove <key>`
**Purpose:** Delete one stored memory entry.

**Usage:**
```text
/memory remove project
```

### `/memory list`
**Purpose:** List all stored memory entries.

**Usage:**
```text
/memory list
```

### `/memory search <text>`
**Purpose:** Search stored memory keys and values for matching text.

**Usage:**
```text
/memory search aura
/memory search toronto
```

### `/memory clear`
**Purpose:** Clear all stored memory.

**Usage:**
```text
/memory clear
```

### `/memory export [path]`
**Purpose:** Export stored memory to a JSON file.

**Usage:**
```text
/memory export
/memory export backup/memory.json
```

### `/memory import <path>`
**Purpose:** Import stored memory from a JSON file.

**Usage:**
```text
/memory import memory_export.json
/memory import backup/memory.json
```

---

## Shared reminder commands

These commands manage Aura's shared reminder store, not the calendar reminder subsystem.

### `/reminder create title=... content=... module=... [remind_at=...]`
**Purpose:** Create a shared reminder entry.

**Usage:**
```text
/reminder create title="Take meds" content="After dinner" module=system
/reminder create title="Leave now" content="Bus in 10" module=calendar remind_at="19:00 24/03/2026"
```

### `/reminder get id=1`
**Purpose:** Fetch one shared reminder by ID.

**Usage:**
```text
/reminder get id=1
```

### `/reminder list`
**Purpose:** List all shared reminders.

**Usage:**
```text
/reminder list
```

### `/reminder delete id=1`
**Purpose:** Delete one shared reminder by ID.

**Usage:**
```text
/reminder delete id=1
```

---

## System commands

### `/system modules`
**Purpose:** List loaded runtime modules.

**Usage:**
```text
/system modules
```

### `/system restart`
**Purpose:** Request a full Aura runtime restart.

**Usage:**
```text
/system restart
```

### `/system shutdown`
**Purpose:** Request runtime shutdown.

**Usage:**
```text
/system shutdown
```

### `/system tasks`
**Purpose:** List registered background tasks known to the task manager.

**Usage:**
```text
/system tasks
```

---

## Debug commands

### `/debug runtime`
**Purpose:** Show runtime lifecycle and interface state, including exit/restart flags and request/response counts.

**Usage:**
```text
/debug runtime
```

### `/debug database`
**Purpose:** Show basic database diagnostics, including connection state.

**Usage:**
```text
/debug database
```

### `/debug calendar`
**Purpose:** Show high-level calendar subsystem diagnostics.

**Usage:**
```text
/debug calendar
```

### `/debug llm`
**Purpose:** Show LLM runtime settings such as model, endpoint, and history limit.

**Usage:**
```text
/debug llm
```

### `/debug logs [line_count]`
**Purpose:** Show the most recent lines from the current log file.

**Usage:**
```text
/debug logs
/debug logs 50
```

### `/debug memory`
**Purpose:** Show high-level memory subsystem diagnostics.

**Usage:**
```text
/debug memory
```

### `/debug notifications`
**Purpose:** Show notification subsystem diagnostics, including due and unread counts.

**Usage:**
```text
/debug notifications
```

### `/debug reminders`
**Purpose:** Show shared reminder subsystem diagnostics.

**Usage:**
```text
/debug reminders
```

### `/debug threading`
**Purpose:** Show threading, task manager, and scheduler state.

**Usage:**
```text
/debug threading
```

### `/debug threading end name=<task_name>`
**Purpose:** Request a stop for a running managed task thread.

**Usage:**
```text
/debug threading end name=schedule_alpha
/debug threading end name=my_background_task
```

**Notes:**
- This requests a cooperative stop through the threading manager.
- It does not forcibly kill Python threads.

---

## Calendar commands

These commands operate on the calendar subsystem and are separate from the shared reminder commands above.

### `/calendar list`
**Purpose:** List all available calendars.

**Usage:**
```text
/calendar list
```

### `/calendar create name=... [description=...] [color=...] [timezone=...] [visibility=...] [is_default=...]`
**Purpose:** Create a new calendar container.

**Usage:**
```text
/calendar create name=Work
/calendar create name=Personal timezone=America/Toronto color=#3ea6ff
```

### `/calendar day day=DD/MM/YYYY [calendar_id=1]`
**Purpose:** Build a day view for a calendar.

**Usage:**
```text
/calendar day day=24/03/2026
/calendar day day=24/03/2026 calendar_id=1
```

### `/calendar week day=DD/MM/YYYY [calendar_id=1]`
**Purpose:** Build a week view anchored on a specific day.

**Usage:**
```text
/calendar week day=24/03/2026
/calendar week day=24/03/2026 calendar_id=1
```

### `/calendar month month=DD/MM/YYYY [calendar_id=1]`
**Purpose:** Build a month view anchored on a specific date.

**Usage:**
```text
/calendar month month=24/03/2026
/calendar month month=24/03/2026 calendar_id=1
```

---

## Calendar event commands

### `/calendar event create title=... start_at=... [end_at=...] [description=...]`
**Purpose:** Create a calendar event.

**Usage:**
```text
/calendar event create title="Meeting" start_at="10:00 24/03/2026"
/calendar event create title="Dinner" start_at="18:00 24/03/2026" end_at="20:00 24/03/2026" description="With Olivia"
```

### `/calendar event get id=1`
**Purpose:** Fetch one calendar event by ID.

**Usage:**
```text
/calendar event get id=1
```

### `/calendar event list ...`
**Purpose:** List or search calendar events.

**Usage:**
```text
/calendar event list start_at="00:00 24/03/2026" end_at="23:59 24/03/2026"
/calendar event list query="meeting"
/calendar event list status=scheduled location=office attendee=nova
```

### `/calendar event update id=1 ...`
**Purpose:** Update one calendar event.

**Usage:**
```text
/calendar event update id=1 title="New title"
/calendar event update id=1 end_at="11:30 24/03/2026"
```

### `/calendar event delete id=1`
**Purpose:** Delete one calendar event.

**Usage:**
```text
/calendar event delete id=1
```

### `/calendar event conflicts start_at=... end_at=... [calendar_id=...] [exclude_event_id=...]`
**Purpose:** Check for overlapping events in a time range.

**Usage:**
```text
/calendar event conflicts start_at="10:00 24/03/2026" end_at="11:00 24/03/2026"
/calendar event conflicts start_at="10:00 24/03/2026" end_at="11:00 24/03/2026" calendar_id=1 exclude_event_id=4
```

---

## Calendar task commands

### `/calendar task create title=... [due_at=...]`
**Purpose:** Create a calendar task.

**Usage:**
```text
/calendar task create title="Pay rent"
/calendar task create title="Send email" due_at="12:00 24/03/2026"
```

### `/calendar task get id=1`
**Purpose:** Fetch one calendar task by ID.

**Usage:**
```text
/calendar task get id=1
```

### `/calendar task list ...`
**Purpose:** List or search calendar tasks.

**Usage:**
```text
/calendar task list
/calendar task list status=pending
/calendar task list query="rent"
/calendar task list priority=high due_before="25:00 24/03/2026"
```

### `/calendar task update id=1 ...`
**Purpose:** Update one calendar task.

**Usage:**
```text
/calendar task update id=1 status=completed
/calendar task update id=1 title="Updated task"
```

### `/calendar task delete id=1`
**Purpose:** Delete one calendar task.

**Usage:**
```text
/calendar task delete id=1
```

---

## Calendar reminder commands

These commands manage reminders inside the calendar subsystem.

### `/calendar reminder create title=... remind_at=...`
**Purpose:** Create a calendar reminder.

**Usage:**
```text
/calendar reminder create title="Leave now" remind_at="12:30 24/03/2026"
/calendar reminder create title="Meeting soon" remind_at="09:45 24/03/2026" event_id=1
```

### `/calendar reminder get id=1`
**Purpose:** Fetch one calendar reminder by ID.

**Usage:**
```text
/calendar reminder get id=1
```

### `/calendar reminder list ...`
**Purpose:** List or search calendar reminders.

**Usage:**
```text
/calendar reminder list
/calendar reminder list calendar_id=1 include_delivered=false
/calendar reminder list query="meeting"
/calendar reminder list event_id=1 remind_before="12:00 24/03/2026"
```

### `/calendar reminder update id=1 ...`
**Purpose:** Update one calendar reminder.

**Usage:**
```text
/calendar reminder update id=1 title="New title"
/calendar reminder update id=1 remind_at="13:00 24/03/2026"
```

### `/calendar reminder delete id=1`
**Purpose:** Delete one calendar reminder.

**Usage:**
```text
/calendar reminder delete id=1
```

### `/calendar reminder processdue`
**Purpose:** Immediately process calendar reminders that are due.

**Usage:**
```text
/calendar reminder processdue
```

---

## Notes

- The command registry is manual by design. Only commands explicitly registered in the CLI branch are available.
- Plain chat remains the normal path for LLM interaction.
- Shared reminders (`/reminder ...`) and calendar reminders (`/calendar reminder ...`) are different systems.
