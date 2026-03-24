"""Centralized database table creation for Aura."""


class DatabaseTableManager:
    """
    Creates and maintains all core Aura database tables.

    This class is the single place where CREATE TABLE statements live.
    """

    def __init__(self, database):
        """
        Initialize the table manager with a database interface.

        Args:
            database:
                Active database adapter with an `execute()` method.
        """

        self.database = database

    def createAllTables(self):
        """
        Create every required Aura table if it does not already exist.
        """

        self.createSystemInfoTable()
        self.createCommandLogsTable()
        self.createConversationHistoryTable()
        self.createMemoryTable()
        self.createNotificationsTable()
        self.createRemindersTable()
        self.createCalendarCalendarsTable()
        self.createCalendarEventsTable()
        self.createCalendarEventExceptionsTable()
        self.createCalendarTasksTable()
        self.createCalendarTaskExceptionsTable()
        self.createCalendarRemindersTable()
        self.createCalendarReminderExceptionsTable()

    def createSystemInfoTable(self):
        """Create the system_info table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS system_info (
                `key` VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
            """
        )

    def createCommandLogsTable(self):
        """Create the command_logs table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS command_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_text TEXT NOT NULL,
                command_root VARCHAR(128),
                status VARCHAR(32) NOT NULL,
                response_text TEXT,
                error_text TEXT,
                duration_ms INT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createConversationHistoryTable(self):
        """Create the conversation_history table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                role VARCHAR(32) NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createMemoryTable(self):
        """Create the memory table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                memory_key VARCHAR(255) PRIMARY KEY,
                value TEXT,
                importance INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createNotificationsTable(self):
        """Create the notifications table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                source_type VARCHAR(64) DEFAULT 'system',
                source_id VARCHAR(128) NULL,
                category VARCHAR(64) DEFAULT 'general',
                title VARCHAR(255) NOT NULL,
                message TEXT,
                payload TEXT NULL,
                priority VARCHAR(32) DEFAULT 'normal',
                status VARCHAR(32) DEFAULT 'pending',
                scheduled_for DATETIME NULL,
                delivered_at DATETIME NULL,
                read_at DATETIME NULL,
                dismissed_at DATETIME NULL,
                expires_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )

    def createRemindersTable(self):
        """Create the reminders table."""
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                remind_at DATETIME NULL,
                delivered_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createCalendarCalendarsTable(self):
        """Create the calendar_calendars table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_calendars (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                color VARCHAR(32),
                timezone VARCHAR(64) DEFAULT 'UTC',
                visibility VARCHAR(32) DEFAULT 'private',
                is_default BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_calendars
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'UTC'
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_calendars
            ADD COLUMN IF NOT EXISTS visibility VARCHAR(32) DEFAULT 'private'
            """
        )

    def createCalendarEventsTable(self):
        """Create the calendar_events table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                calendar_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                location VARCHAR(255),
                attendees TEXT,
                organizer VARCHAR(255) NULL,
                timezone VARCHAR(64) DEFAULT 'UTC',
                visibility VARCHAR(32) DEFAULT 'private',
                categories TEXT NULL,
                notification_preferences TEXT NULL,
                linked_task_id INT NULL,
                start_at DATETIME NOT NULL,
                end_at DATETIME NULL,
                all_day BOOLEAN DEFAULT FALSE,
                status VARCHAR(32) DEFAULT 'confirmed',
                recurrence_type VARCHAR(32) NULL,
                recurrence_interval INT DEFAULT 1,
                recurrence_until DATETIME NULL,
                recurrence_count INT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS attendees TEXT
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS organizer VARCHAR(255) NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'UTC'
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS visibility VARCHAR(32) DEFAULT 'private'
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS categories TEXT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS notification_preferences TEXT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS linked_task_id INT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS recurrence_type VARCHAR(32) NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS recurrence_interval INT DEFAULT 1
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS recurrence_until DATETIME NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS recurrence_count INT NULL
            """
        )

    def createCalendarTasksTable(self):
        """Create the calendar_tasks table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                calendar_id INT NOT NULL,
                linked_event_id INT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                timezone VARCHAR(64) DEFAULT 'UTC',
                categories TEXT NULL,
                notification_preferences TEXT NULL,
                due_at DATETIME NULL,
                priority VARCHAR(32) DEFAULT 'normal',
                status VARCHAR(32) DEFAULT 'pending',
                recurrence_type VARCHAR(32) NULL,
                recurrence_interval INT DEFAULT 1,
                recurrence_until DATETIME NULL,
                recurrence_count INT NULL,
                completed_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS linked_event_id INT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'UTC'
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS categories TEXT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS notification_preferences TEXT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS recurrence_type VARCHAR(32) NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS recurrence_interval INT DEFAULT 1
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS recurrence_until DATETIME NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_tasks
            ADD COLUMN IF NOT EXISTS recurrence_count INT NULL
            """
        )

    def createCalendarEventExceptionsTable(self):
        """Create the calendar_event_exceptions table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_event_exceptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_id INT NOT NULL,
                occurrence_start DATETIME NOT NULL,
                exception_type VARCHAR(32) NOT NULL,
                override_title VARCHAR(255) NULL,
                override_description TEXT NULL,
                override_location VARCHAR(255) NULL,
                override_attendees TEXT NULL,
                override_start_at DATETIME NULL,
                override_end_at DATETIME NULL,
                override_all_day BOOLEAN NULL,
                override_status VARCHAR(32) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createCalendarRemindersTable(self):
        """Create the calendar_reminders table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                calendar_id INT NOT NULL,
                event_id INT NULL,
                task_id INT NULL,
                title VARCHAR(255) NOT NULL,
                notes TEXT,
                timezone VARCHAR(64) DEFAULT 'UTC',
                notification_preferences TEXT NULL,
                remind_at DATETIME NOT NULL,
                recurrence_type VARCHAR(32) NULL,
                recurrence_interval INT DEFAULT 1,
                recurrence_until DATETIME NULL,
                recurrence_count INT NULL,
                delivered_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_reminders
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'UTC'
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_reminders
            ADD COLUMN IF NOT EXISTS notification_preferences TEXT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_reminders
            ADD COLUMN IF NOT EXISTS recurrence_type VARCHAR(32) NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_reminders
            ADD COLUMN IF NOT EXISTS recurrence_interval INT DEFAULT 1
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_reminders
            ADD COLUMN IF NOT EXISTS recurrence_until DATETIME NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE calendar_reminders
            ADD COLUMN IF NOT EXISTS recurrence_count INT NULL
            """
        )
        self.database.execute(
            """
            ALTER TABLE reminders
            ADD COLUMN IF NOT EXISTS delivered_at DATETIME NULL
            """
        )

    def createCalendarTaskExceptionsTable(self):
        """Create the calendar_task_exceptions table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_task_exceptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL,
                occurrence_due_at DATETIME NOT NULL,
                exception_type VARCHAR(32) NOT NULL,
                override_title VARCHAR(255) NULL,
                override_description TEXT NULL,
                override_due_at DATETIME NULL,
                override_priority VARCHAR(32) NULL,
                override_status VARCHAR(32) NULL,
                override_categories TEXT NULL,
                override_notification_preferences TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def createCalendarReminderExceptionsTable(self):
        """Create the calendar_reminder_exceptions table."""

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_reminder_exceptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                reminder_id INT NOT NULL,
                occurrence_remind_at DATETIME NOT NULL,
                exception_type VARCHAR(32) NOT NULL,
                override_title VARCHAR(255) NULL,
                override_notes TEXT NULL,
                override_remind_at DATETIME NULL,
                override_notification_preferences TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

