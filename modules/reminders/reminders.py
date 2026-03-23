"""Reminder persistence and CRUD operations."""


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

        if self.logger:
            self.logger.info("Initialized.")

    def createRemindersTable(self):
        """
        Validate database availability for reminder persistence.

        Table creation is centralized in modules.database.databaseTableManager.
        """

        if not self.database and self.logger:
            self.logger.warning("Reminders started without a database.")

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

        self.database.execute(
            """
            INSERT INTO reminders (title, remind_at)
            VALUES (?, ?)
            """,
            (title, remind_at),
        )

    def listReminders(self):
        """
        Return all reminders ordered by creation time descending.
        """

        if not self.database:
            return []

        return self.database.fetchAll(
            """
            SELECT id, title, remind_at, created_at
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
