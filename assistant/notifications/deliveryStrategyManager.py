"""Determine how notifications should be delivered."""

from __future__ import annotations

from assistant.notifications.models.notificationDeliveryMode import NotificationDeliveryMode
from assistant.notifications.models.notificationPriority import NotificationPriority
from assistant.notifications.models.notificationRoute import NotificationRoute


class DeliveryStrategyManager:
    """Choose the appropriate delivery mode for each notification."""

    def chooseRoute(self, notification, context):
        """Return the best delivery route for the current notification."""

        priority = NotificationPriority.normalize(notification.priority)
        conversationActive = bool(getattr(context, "conversationActive", False))
        voiceSpeaking = bool(getattr(context, "voiceSpeaking", False))
        quietHours = bool(getattr(context, "quietHoursActive", False))
        allowVoiceInterruptions = bool(getattr(context, "allowVoiceInterruptions", True))
        criticalAlwaysInterrupt = bool(getattr(context, "criticalAlwaysInterrupt", True))
        interfaceType = str(getattr(context, "interfaceType", "desktop") or "desktop").lower()

        if priority == NotificationPriority.EMERGENCY:
            return NotificationRoute(
                deliveryMode=NotificationDeliveryMode.INTERRUPT,
                interrupt=True,
                voice=True,
                ui=True,
                persistent=True,
                queue=False,
                suppressible=False,
                reason="emergency",
            )

        if priority == NotificationPriority.CRITICAL:
            interrupt = bool(criticalAlwaysInterrupt and allowVoiceInterruptions)
            return NotificationRoute(
                deliveryMode=NotificationDeliveryMode.INTERRUPT if interrupt else NotificationDeliveryMode.VOICE_AND_UI,
                interrupt=interrupt,
                voice=True,
                ui=True,
                persistent=True,
                queue=False,
                suppressible=False,
                reason="critical",
            )

        if priority == NotificationPriority.HIGH:
            interrupt = bool((conversationActive or voiceSpeaking) and allowVoiceInterruptions)
            return NotificationRoute(
                deliveryMode=NotificationDeliveryMode.VOICE_AND_UI if not interrupt else NotificationDeliveryMode.INTERRUPT,
                interrupt=interrupt,
                voice=True,
                ui=True,
                persistent=True,
                queue=False,
                suppressible=False,
                reason="high_priority",
            )

        if priority == NotificationPriority.NORMAL:
            voice = bool(interfaceType in {"voice", "speaker"} and not quietHours)
            return NotificationRoute(
                deliveryMode=NotificationDeliveryMode.VOICE_AND_UI if voice else NotificationDeliveryMode.UI_ONLY,
                interrupt=False,
                voice=voice,
                ui=True,
                persistent=False,
                queue=True,
                suppressible=True,
                reason="normal_priority",
            )

        if priority == NotificationPriority.LOW:
            if quietHours or conversationActive:
                return NotificationRoute(
                    deliveryMode=NotificationDeliveryMode.SILENT,
                    interrupt=False,
                    voice=False,
                    ui=True,
                    persistent=False,
                    queue=True,
                    suppressible=True,
                    reason="low_priority_deferred",
                )
            return NotificationRoute(
                deliveryMode=NotificationDeliveryMode.UI_ONLY,
                interrupt=False,
                voice=False,
                ui=True,
                persistent=False,
                queue=True,
                suppressible=True,
                reason="low_priority",
            )

        return NotificationRoute(
            deliveryMode=NotificationDeliveryMode.UI_ONLY,
            interrupt=False,
            voice=False,
            ui=True,
            persistent=False,
            queue=True,
            suppressible=True,
            reason="default",
        )
