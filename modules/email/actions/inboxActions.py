"""Inbox-specific email actions."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


INBOX_ACTIONS = (
    ModuleAction(
        name="email.filterEmails",
        description="Filter messages using a structured query.",
        method="filterEmails",
        permissions=("email.filter",),
        capabilities=("email.filter",),
        target="filterEmails",
    ),
    ModuleAction(
        name="email.sortEmails",
        description="Sort messages using a selected mode.",
        method="sortEmails",
        permissions=("email.sort",),
        capabilities=("email.sort",),
        target="sortEmails",
    ),
    ModuleAction(
        name="email.archiveEmail",
        description="Archive one email message.",
        method="archiveEmail",
        parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}},
        requiredParameters=("messageId",),
        permissions=("email.archive",),
        capabilities=("email.read",),
        target="archiveEmail",
    ),
    ModuleAction(
        name="email.deleteEmail",
        description="Delete one email message.",
        method="deleteEmail",
        parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}},
        requiredParameters=("messageId",),
        permissions=("email.delete",),
        capabilities=("email.read",),
        target="deleteEmail",
    ),
)
