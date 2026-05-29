"""Notification panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class NotificationPanel(TextPanel):
    """Display assistant notifications and alerts."""

    title = "Notifications"

    def refresh(self, snapshot):
        notificationCenter = getattr(snapshot, "notificationCenter", {}) or {}
        lines = ["[NOTIFICATIONS]"]
        lines.append(
            "State: "
            f"{'enabled' if notificationCenter.get('enabled') else 'disabled'}, "
            f"active={len(notificationCenter.get('active') or [])}, "
            f"delivered={len(notificationCenter.get('delivered') or [])}, "
            f"suppressed={len(notificationCenter.get('suppressed') or [])}, "
            f"escalated={len(notificationCenter.get('escalated') or [])}"
        )

        recentNotifications = list(notificationCenter.get("delivered") or []) + list(notificationCenter.get("active") or [])
        if not recentNotifications and not snapshot.notifications:
            lines.append("No notifications observed.")

        for notification in (recentNotifications[-10:] if recentNotifications else snapshot.notifications[-10:]):
            payload = notification.get("metadata", {}) if isinstance(notification, dict) else {}
            title = notification.get("title") if isinstance(notification, dict) else ""
            message = notification.get("message") if isinstance(notification, dict) else ""
            priority = notification.get("priority") if isinstance(notification, dict) else ""
            source = notification.get("source") if isinstance(notification, dict) else ""
            if not title and not message and isinstance(notification, dict):
                payload = notification.get("payload", {})
                title = payload.get("title") or payload.get("name") or ""
                message = payload.get("message") or payload.get("content") or ""
                priority = payload.get("priority", "")
                source = payload.get("source") or payload.get("source_module") or ""
            lines.append("")
            lines.append(f"[{priority}] {title or message or source}")
            if source:
                lines.append(f"Source: {source}")
            if message and message != title:
                lines.append(f"Message: {message}")
        self.setText("\n".join(str(line) for line in lines))
