"""Notification persistence API for Aura."""

from __future__ import annotations

from datetime import datetime
from typing import Optional


class Notifications:
    """
    Store and query notifications for any Aura interface branch.

    Notifications are persisted in the database and exposed through a small,
    interface-agnostic API. Other modules can queue alerts by supplying a
    title, content body, due datetime, and the module or system name that
    created the notification.
    """

    def __init__(self, context):
        """
        Initialize the notifications service.

        Args:
            context:
                Runtime context providing database access and optional logging.
        """

        self.context = context
        self.database = context.database
        self.logger = context.logger.getChild("Notifications") if context.logger else None

        self.createNotificationsTable()

        if self.logger:
            self.logger.info("Initialized.")

    def createNotificationsTable(self):
        """
        Validate notification persistence availability.

        Physical table creation is centralized in DatabaseTableManager.
        """

        if not self.database and self.logger:
            self.logger.warning("Notifications started without a database.")

    def createNotification(
        self,
        source_module: str,
        title: str,
        content: str,
        timestamp: str,
    ) -> Optional[int]:
        """
        Persist one queued notification.

        Args:
            source_module:
                Name of the module or system that queued the notification.
            title:
                Short notification title.
            content:
                Full notification body text.
            timestamp:
                Datetime string indicating when the notification should fire.

        Returns:
            int | None:
                Unique notification ID when persistence succeeds.
        """

        if not self.database:
            return None

        cursor = self.database.execute(
            """
            INSERT INTO notifications (title, content, notification_at, source_module)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(title),
                str(content),
                self.context.dtUtil.toStorageDateTime(timestamp),
                str(source_module),
            ),
        )
        last_row_id = getattr(cursor, "lastrowid", None)
        if last_row_id is not None:
            return int(last_row_id)

        row = self.database.fetchOne(
            """
            SELECT id
            FROM notifications
            ORDER BY id DESC
            LIMIT 1
            """
        )
        if row is None:
            return None
        return int(row["id"])

    def listNotifications(self, status: Optional[str] = None, limit: Optional[int] = None):
        """
        Return notifications ordered by their scheduled datetime.

        Args:
            status:
                Optional status filter such as `pending`, `delivered`, `read`,
                or `dismissed`.
            limit:
                Optional maximum number of rows to return.
        """

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT id, title, content, notification_at, source_module, status,
                   delivered_at, read_at, dismissed_at, created_at, updated_at
            FROM notifications
            ORDER BY notification_at ASC, id ASC
            """
        )

        normalized_status = str(status).strip().lower() if status is not None else None
        prepared_rows = []
        for row in rows:
            prepared = dict(row)
            if normalized_status and str(prepared.get("status") or "").lower() != normalized_status:
                continue
            prepared_rows.append(prepared)

        if limit is not None:
            return prepared_rows[: int(limit)]
        return prepared_rows

    def getNotification(self, notification_id: int):
        """
        Return one notification row by ID.
        """

        if not self.database:
            return None

        return self.database.fetchOne(
            """
            SELECT id, title, content, notification_at, source_module, status,
                   delivered_at, read_at, dismissed_at, created_at, updated_at
            FROM notifications
            WHERE id = ?
            """,
            (int(notification_id),),
        )

    def listDueNotifications(self, current_time: Optional[str] = None):
        """
        Return notifications whose scheduled time has arrived and are still pending.

        Args:
            current_time:
                Optional comparison datetime. Defaults to the current UTC time.
        """

        comparison_time = (
            self.context.dtUtil.toStorageDateTime(current_time)
            if current_time is not None
            else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )

        rows = self.listNotifications(status="pending")
        return [
            row for row in rows
            if row.get("notification_at") is not None and row["notification_at"] <= comparison_time
        ]

    def executeNotification(self, notification_id: int):
        """
        Execute one notification through the CLI interface.

        The CLI branch delivers notifications directly to stdout so scheduled
        reminders and alert-producing modules remain visible without a separate
        desktop or mobile notification layer.
        """
        notification = self.getNotification(notification_id)
        if notification is None:
            raise ValueError(f"Notification does not exist: {notification_id}")

        print(
            f"[NOTIFICATION] {notification.get('title') or ''}\n"
            f"{notification.get('content') or ''}"
        )
        self.markDelivered(notification_id)
        return notification

    def sendNotification(self, notification_id: int):
        """
        Send one notification through the active branch delivery behavior.
        """
        return self.executeNotification(notification_id)

    def markDelivered(self, notification_id: int):
        """
        Mark one notification as delivered.
        """

        self._updateNotificationStatus(
            notification_id=notification_id,
            status="delivered",
            timestamp_field="delivered_at",
        )

    def markRead(self, notification_id: int):
        """
        Mark one notification as read.
        """

        self._updateNotificationStatus(
            notification_id=notification_id,
            status="read",
            timestamp_field="read_at",
        )

    def dismissNotification(self, notification_id: int):
        """
        Mark one notification as dismissed.
        """

        self._updateNotificationStatus(
            notification_id=notification_id,
            status="dismissed",
            timestamp_field="dismissed_at",
        )

    def deleteNotification(self, notification_id: int):
        """
        Delete one notification row.
        """

        if not self.database:
            return

        self.database.execute(
            "DELETE FROM notifications WHERE id = ?",
            (int(notification_id),),
        )

    def _updateNotificationStatus(self, notification_id: int, status: str, timestamp_field: str):
        """
        Update a notification status and the matching lifecycle timestamp.
        """

        if not self.database:
            return

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.database.execute(
            f"UPDATE notifications SET status = ?, {timestamp_field} = ? WHERE id = ?",
            (str(status), timestamp, int(notification_id)),
        )
