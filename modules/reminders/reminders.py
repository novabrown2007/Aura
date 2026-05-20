"""Reminder persistence and notification queueing for Aura."""

from modules.base import AuraModule, ModuleMetadata
from core.threading.scheduler.schedule import Schedule


class Reminders(AuraModule):
    """
    Reminder data layer for creating, listing, deleting, and queueing reminders.
    """

    metadata = ModuleMetadata(
        name="reminders",
        version="1.0.0",
        description="Reminder creation, storage, and due reminder processing.",
        dependencies=("notifications",),
        permissions=("database:read", "database:write", "scheduler:write"),
        capabilities=("reminders", "notifications"),
    )

    def __init__(self, context=None):
        """
        Initialize the reminder manager and ensure schema exists.
        """

        super().__init__()
        self.database = None
        self.logger = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Initialize the reminders module."""

        super().initialize(context)
        self.context = context
        self.database = context.database

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Reminders")

        self.createRemindersTable()
        self._registerReminderPollingSchedule()

        if self.logger:
            self.logger.info("Initialized.")

    def getIntents(self):
        """Return intents handled by reminders."""

        return []

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

    def createReminder(
        self,
        title: str,
        content: str,
        module_of_origin: str,
        reminder_at: str = None,
    ):
        """
        Insert a new reminder row.

        Args:
            title:
                Reminder title/message.
            content:
                Reminder body content.
            module_of_origin:
                Name of the module or system that created the reminder.
            reminder_at:
                Optional scheduled datetime for queueing the reminder notification.
        """

        if not self.database:
            return None

        normalized_reminder_at = (
            self.context.dtUtil.toStorageDateTime(reminder_at)
            if reminder_at is not None
            else None
        )

        cursor = self.database.execute(
            """
            INSERT INTO reminders (title, content, reminder_at, module_of_origin)
            VALUES (?, ?, ?, ?)
            """,
            (str(title), str(content), normalized_reminder_at, str(module_of_origin)),
        )
        last_row_id = getattr(cursor, "lastrowid", None)
        if last_row_id is not None:
            return int(last_row_id)

        row = self.database.fetchOne(
            """
            SELECT id
            FROM reminders
            ORDER BY id DESC
            LIMIT 1
            """
        )
        if row is None:
            return None
        return int(row["id"])

    def getReminder(self, reminder_id: int):
        """
        Return one reminder row by ID.
        """

        if not self.database:
            return None

        return self.database.fetchOne(
            """
            SELECT id, title, content, reminder_at, module_of_origin,
                   notification_id, sent_at, created_at
            FROM reminders
            WHERE id = ?
            """,
            (int(reminder_id),),
        )

    def listReminders(self):
        """
        Return all reminders ordered by scheduled time and ID.
        """

        if not self.database:
            return []

        return self.database.fetchAll(
            """
            SELECT id, title, content, reminder_at, module_of_origin,
                   notification_id, sent_at, created_at
            FROM reminders
            ORDER BY reminder_at ASC, id ASC
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
        Find due reminders and queue matching notification records.

        Returns:
            list[dict]:
                Due reminder rows that were processed during this poll cycle.
        """

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT id, title, content, reminder_at, module_of_origin,
                   notification_id, sent_at, created_at
            FROM reminders
            WHERE reminder_at IS NOT NULL
              AND sent_at IS NULL
              AND reminder_at <= NOW()
            ORDER BY reminder_at ASC, id ASC
            """
        )

        for row in rows:
            self.sendReminder(int(row["id"]))

        return rows

    def sendReminder(self, reminder_id: int):
        """
        Turn one reminder into a queued notification.
        """

        reminder = self.getReminder(reminder_id)
        if reminder is None:
            raise ValueError(f"Reminder does not exist: {reminder_id}")

        notifications = self.context.require("notifications")
        notification_id = notifications.createNotification(
            reminder["module_of_origin"],
            reminder["title"],
            reminder.get("content") or "",
            self.context.dtUtil.toPreferredDateTime(reminder["reminder_at"]),
        )

        self.database.execute(
            """
            UPDATE reminders
            SET notification_id = ?, sent_at = NOW()
            WHERE id = ?
            """,
            (notification_id, int(reminder_id)),
        )

        return notification_id
