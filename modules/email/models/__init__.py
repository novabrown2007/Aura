"""Email models for Aura."""

from modules.email.models.emailAccount import EmailAccount
from modules.email.models.emailAddress import EmailAddress
from modules.email.models.emailAttachment import EmailAttachment
from modules.email.models.emailConnectionState import EmailConnectionState
from modules.email.models.emailDraft import EmailDraft
from modules.email.models.emailFilter import EmailFilter
from modules.email.models.emailLabel import EmailLabel
from modules.email.models.emailMessage import EmailMessage
from modules.email.models.emailNotificationRule import EmailNotificationRule
from modules.email.models.emailProviderType import EmailProviderType
from modules.email.models.emailSortMode import EmailSortMode
from modules.email.models.emailTag import EmailTag
from modules.email.models.scheduledEmail import ScheduledEmail

__all__ = [
    "EmailAccount",
    "EmailAddress",
    "EmailAttachment",
    "EmailConnectionState",
    "EmailDraft",
    "EmailFilter",
    "EmailLabel",
    "EmailMessage",
    "EmailNotificationRule",
    "EmailProviderType",
    "EmailSortMode",
    "EmailTag",
    "ScheduledEmail",
]
