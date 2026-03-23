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
        Create the reminders table if it does not already exist.
        """

        if not self.database:
            return

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                remind_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
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

