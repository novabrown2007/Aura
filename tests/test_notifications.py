"""Tests for Aura's notification storage API."""

import unittest
from unittest.mock import patch

from modules.notifications.notifications import Notifications
from tests.support.fakes import make_context


class _NotificationDatabase:
    """In-memory notification database stub used by backend tests."""

    def __init__(self):
        """Initialize stored notification rows and query tracking."""

        self.executed = []
        self.notifications = []
        self.next_id = 1

    def execute(self, query, params=()):
        """Record write operations and mutate in-memory rows."""

        self.executed.append((query, params))
        normalized = " ".join(query.lower().split())

        if "insert into notifications" in normalized:
            notification_id = self.next_id
            self.notifications.append(
                {
                    "id": notification_id,
                    "title": params[0],
                    "content": params[1],
                    "notification_at": params[2],
                    "source_module": params[3],
                    "status": "pending",
                    "delivered_at": None,
                    "read_at": None,
                    "dismissed_at": None,
                    "created_at": "2026-03-24 00:00:00",
                    "updated_at": "2026-03-24 00:00:00",
                }
            )
            self.next_id += 1
            return type("Cursor", (), {"lastrowid": notification_id})()

        if normalized.startswith("update notifications set status = ?, delivered_at = ? where id ="):
            status, delivered_at, notification_id = params
            for row in self.notifications:
                if row["id"] == notification_id:
                    row["status"] = status
                    row["delivered_at"] = delivered_at
            return

        if normalized.startswith("update notifications set status = ?, read_at = ? where id ="):
            status, read_at, notification_id = params
            for row in self.notifications:
                if row["id"] == notification_id:
                    row["status"] = status
                    row["read_at"] = read_at
            return

        if normalized.startswith("update notifications set status = ?, dismissed_at = ? where id ="):
            status, dismissed_at, notification_id = params
            for row in self.notifications:
                if row["id"] == notification_id:
                    row["status"] = status
                    row["dismissed_at"] = dismissed_at
            return

        if normalized.startswith("delete from notifications where id ="):
            notification_id = params[0]
            self.notifications = [row for row in self.notifications if row["id"] != notification_id]
        return None

    def fetchAll(self, query, params=()):
        """Return stored notifications for list queries."""

        normalized = " ".join(query.lower().split())
        if "from notifications" not in normalized:
            return []
        return [dict(row) for row in self.notifications]

    def fetchOne(self, query, params=()):
        """Return one notification row for ID-based lookups."""

        normalized = " ".join(query.lower().split())
        if "from notifications" not in normalized:
            return None

        notification_id = params[0]
        for row in self.notifications:
            if row["id"] == notification_id:
                return dict(row)
        return None


class NotificationsTests(unittest.TestCase):
    """Validate notification creation and lifecycle operations."""

    def _create_notifications(self):
        """Build a notification service with an in-memory database stub."""

        database = _NotificationDatabase()
        context = make_context(database=database)
        notifications = Notifications(context)
        return notifications, database

    def test_create_notification_persists_requested_fields(self):
        """Creating a notification should store title, content, datetime, and source module."""

        notifications, database = self._create_notifications()

        notification_id = notifications.createNotification(
            source_module="system",
            title="Server Restart",
            content="The runtime will restart tonight.",
            timestamp="22:15 24/03/2026",
        )

        row = database.notifications[-1]
        self.assertEqual(notification_id, 1)
        self.assertEqual(row["title"], "Server Restart")
        self.assertEqual(row["content"], "The runtime will restart tonight.")
        self.assertEqual(row["notification_at"], "2026-03-24 22:15:00")
        self.assertEqual(row["source_module"], "system")

    def test_list_due_notifications_returns_pending_items_before_cutoff(self):
        """Due notification lookup should return only pending rows at or before the comparison time."""

        notifications, _database = self._create_notifications()
        notifications.createNotification("calendar", "A", "First", "08:00 24/03/2026")
        notifications.createNotification("calendar", "B", "Second", "20:00 24/03/2026")

        due_rows = notifications.listDueNotifications(current_time="2026-03-24 12:00")

        self.assertEqual(len(due_rows), 1)
        self.assertEqual(due_rows[0]["title"], "A")

    @patch("modules.notifications.notifications.datetime")
    def test_marking_notification_updates_lifecycle_state(self, mock_datetime):
        """Delivered, read, and dismissed operations should update row state."""

        notifications, database = self._create_notifications()
        notifications.createNotification("calendar", "A", "First", "08:00 24/03/2026")

        mock_datetime.utcnow.return_value.strftime.return_value = "2026-03-24 09:00:00"

        notifications.markDelivered(1)
        self.assertEqual(database.notifications[0]["status"], "delivered")
        self.assertEqual(database.notifications[0]["delivered_at"], "2026-03-24 09:00:00")

        notifications.markRead(1)
        self.assertEqual(database.notifications[0]["status"], "read")
        self.assertEqual(database.notifications[0]["read_at"], "2026-03-24 09:00:00")

        notifications.dismissNotification(1)
        self.assertEqual(database.notifications[0]["status"], "dismissed")
        self.assertEqual(database.notifications[0]["dismissed_at"], "2026-03-24 09:00:00")

    def test_delete_notification_removes_row(self):
        """Deleting a notification should remove it from storage."""

        notifications, database = self._create_notifications()
        notifications.createNotification("calendar", "A", "First", "08:00 24/03/2026")

        notifications.deleteNotification(1)

        self.assertEqual(database.notifications, [])

    def test_execute_notification_prints_and_marks_delivered(self):
        """CLI execution should print the notification and mark it delivered."""

        notifications, database = self._create_notifications()
        notifications.createNotification("system", "Server Restart", "The runtime will restart tonight.", "22:15 24/03/2026")

        with patch("builtins.print") as mock_print, \
                patch("modules.notifications.notifications.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value.strftime.return_value = "2026-03-24 22:15:30"
            row = notifications.executeNotification(1)

        mock_print.assert_called_once_with("[NOTIFICATION] Server Restart\nThe runtime will restart tonight.")
        self.assertEqual(row["id"], 1)
        self.assertEqual(database.notifications[0]["status"], "delivered")
        self.assertEqual(database.notifications[0]["delivered_at"], "2026-03-24 22:15:30")


if __name__ == "__main__":
    unittest.main()
