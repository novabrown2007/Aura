"""Inbox email intents."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


INBOX_INTENTS = (
    ModuleIntent(name="email.listInbox", description="List messages in the inbox.", target="listInbox"),
    ModuleIntent(name="email.readEmail", description="Read one email message.", target="readEmail"),
    ModuleIntent(name="email.filterEmails", description="Filter the inbox.", target="filterEmails"),
    ModuleIntent(name="email.sortEmails", description="Sort the inbox.", target="sortEmails"),
    ModuleIntent(name="email.deleteEmail", description="Delete one email message.", target="deleteEmail"),
    ModuleIntent(name="email.archiveEmail", description="Archive one email message.", target="archiveEmail"),
)
