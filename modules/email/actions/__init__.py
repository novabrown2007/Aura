"""Email action descriptors."""

from modules.email.actions.draftActions import DRAFT_ACTIONS
from modules.email.actions.emailActions import EMAIL_ACTIONS
from modules.email.actions.inboxActions import INBOX_ACTIONS
from modules.email.actions.labelActions import LABEL_ACTIONS
from modules.email.actions.scheduleEmailActions import SCHEDULE_EMAIL_ACTIONS

__all__ = [
    "DRAFT_ACTIONS",
    "EMAIL_ACTIONS",
    "INBOX_ACTIONS",
    "LABEL_ACTIONS",
    "SCHEDULE_EMAIL_ACTIONS",
]
