"""Reminder persistence and CRUD operations."""

from datetime import datetime
from core.threading.events.events import Event
from core.threading.scheduler.schedule import Schedule


class Reminders:
    """
    Reminder data layer for creating, listing, and deleting reminders.
    """

    def __init__(self, context):
        """
        Initialize the reminder manager and ensure schema exists.
        """

        self.context = context
        self.database = context.database

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Reminders")

        self.createRemindersTable()
        self._registerReminderPollingSchedule()

        if self.logger:
            self.logger.info("Initialized.")

    def createRemindersTable(self):
        """
        Validate database availability for reminder persistence.

        Table creation is centralized in modules.database.databaseTableManager.
        """

        if not self.database and self.logger:
            self.logger.warning("Reminders started without a database.")

    def _registerReminderPollingSchedule(self):
        """
        Register a repeating scheduler job that checks for due reminders.
        """

        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None:
            return

        schedule_name = "reminders_poll_due"
        if scheduler.getSchedule(schedule_name) is not None:
            return

        scheduler.addSchedule(
            Schedule(
                name=schedule_name,
                target=self.processDueReminders,
                interval=15.0,
            )
        )

    def createReminder(self, title: str, remind_at: str = None):
        """
        Insert a new reminder row.

        Args:
            title (str):
                Reminder title/message.
            remind_at (str | None):
                Optional datetime string for reminder schedule.
        """

        if not self.database:
            return

        normalized_remind_at = self._normalizeReminderDatetime(remind_at)

        self.database.execute(
            """
            INSERT INTO reminders (title, remind_at)
            VALUES (?, ?)
            """,
            (title, normalized_remind_at),
        )

    def listReminders(self):
        """
        Return all reminders ordered by creation time descending.
        """

        if not self.database:
            return []

        return self.database.fetchAll(
            """
            SELECT id, title, remind_at, delivered_at, created_at
            FROM reminders
            ORDER BY id DESC
            """
        )

    def deleteReminder(self, reminder_id: int):
        """
        Delete one reminder by ID.

        Args:
            reminder_id (int):
                Reminder row ID.
        """

        if not self.database:
            return

        self.database.execute(
            "DELETE FROM reminders WHERE id = ?",
            (reminder_id,),
        )

    def processDueReminders(self):
        """
        Find due reminders, mark them as delivered, and emit reminder events.

        Returns:
            list[dict]:
                Due reminder rows that were emitted during this poll cycle.
        """

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT id, title, remind_at, delivered_at, created_at
            FROM reminders
            WHERE remind_at IS NOT NULL
              AND delivered_at IS NULL
              AND remind_at <= NOW()
            ORDER BY remind_at ASC, id ASC
            """
        )

        for row in rows:
            reminder_id = row.get("id")
            self.database.execute(
                """
                UPDATE reminders
                SET delivered_at = NOW()
                WHERE id = ?
                """,
                (reminder_id,),
            )

            if getattr(self.context, "eventManager", None):
                self.context.eventManager.emit(
                    Event(
                        "reminder_triggered",
                        {
                            "id": reminder_id,
                            "title": row.get("title"),
                            "remind_at": row.get("remind_at"),
                            "created_at": row.get("created_at"),
                        },
                    )
                )

        return rows

    def _normalizeReminderDatetime(self, remind_at: str = None):
        """
        Normalize reminder datetime input into MySQL DATETIME format.

        Accepted examples:
        - `17:00 24/03/2026`
        - `1700 24/03/2026`
        - `17:00`
        - `1700`

        Args:
            remind_at (str | None):
                Raw reminder datetime string from commands or UI.

        Returns:
            str | None:
                Datetime formatted as `YYYY-MM-DD HH:MM:SS`, or `None`
                when no reminder time was provided.

        Raises:
            ValueError:
                If the input cannot be parsed into a valid datetime.
        """

        if remind_at is None:
            return None

        raw_value = str(remind_at).strip()
        if raw_value == "":
            return None

        parts = raw_value.split()
        if len(parts) not in {1, 2}:
            raise ValueError(
                "Invalid reminder date/time. Use HH:MM DD/MM/YYYY "
                "(example: 17:00 24/03/2026)."
            )

        time_part = parts[0]
        date_part = parts[1] if len(parts) == 2 else None
        time_digits = "".join(character for character in time_part if character.isdigit())

        if len(time_digits) == 4:
            normalized_time = f"{time_digits[0:2]}:{time_digits[2:4]}:00"
        elif len(time_digits) == 6:
            normalized_time = f"{time_digits[0:2]}:{time_digits[2:4]}:{time_digits[4:6]}"
        else:
            raise ValueError(
                "Invalid reminder time. Use HH:MM "
                "(example: 17:00)."
            )

        if date_part is None:
            normalized_date = datetime.now().strftime("%Y-%m-%d")
        else:
            date_digits = "".join(character for character in date_part if character.isdigit())
            if len(date_digits) != 8:
                raise ValueError(
                    "Invalid reminder date. Use DD/MM/YYYY "
                    "(example: 24/03/2026)."
                )
            normalized_date = (
                f"{date_digits[4:8]}-{date_digits[2:4]}-{date_digits[0:2]}"
            )

        normalized_datetime = f"{normalized_date} {normalized_time}"

        try:
            parsed = datetime.strptime(normalized_datetime, "%Y-%m-%d %H:%M:%S")
        except ValueError as error:
            raise ValueError(
                "Invalid reminder date/time. Use HH:MM DD/MM/YYYY "
                "(example: 17:00 24/03/2026)."
            ) from error

        return parsed.strftime("%Y-%m-%d %H:%M:%S")
