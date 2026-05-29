"""Assistant attention-management layer for Aura notifications."""

from assistant.notifications.deliveryStrategyManager import DeliveryStrategyManager
from assistant.notifications.escalationManager import EscalationManager
from assistant.notifications.handlers.notificationEventHandler import NotificationEventHandler
from assistant.notifications.interruptionManager import InterruptionManager
from assistant.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationContext,
    NotificationDeliveryMode,
    NotificationPriority,
    NotificationRoute,
)
from assistant.notifications.notificationHistory import NotificationHistory
from assistant.notifications.notificationManager import NotificationManager
from assistant.notifications.notificationPriorityEngine import NotificationPriorityEngine
from assistant.notifications.notificationQueue import NotificationQueue
from assistant.notifications.notificationRouter import NotificationRouter
from assistant.notifications.notificationSuppression import NotificationSuppression

__all__ = [
    "DeliveryStrategyManager",
    "EscalationManager",
    "InterruptionManager",
    "Notification",
    "NotificationCategory",
    "NotificationContext",
    "NotificationDeliveryMode",
    "NotificationEventHandler",
    "NotificationHistory",
    "NotificationManager",
    "NotificationPriority",
    "NotificationPriorityEngine",
    "NotificationQueue",
    "NotificationRoute",
    "NotificationRouter",
    "NotificationSuppression",
]
