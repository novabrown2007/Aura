"""Draft and send email intents."""

from __future__ import annotations

from core.modules.base.moduleIntent import ModuleIntent


DRAFT_INTENTS = (
    ModuleIntent(name="email.listDrafts", description="List saved drafts.", target="listDrafts"),
    ModuleIntent(name="email.createDraft", description="Create a draft email.", target="createDraft"),
    ModuleIntent(name="email.updateDraft", description="Update a draft email.", target="updateDraft"),
    ModuleIntent(name="email.sendEmail", description="Send an email.", target="sendEmail"),
    ModuleIntent(name="email.scheduleEmail", description="Schedule an email for later.", target="scheduleEmail"),
    ModuleIntent(name="email.listLabels", description="List email labels.", target="listLabels"),
    ModuleIntent(name="email.applyLabel", description="Apply a label to a message.", target="applyLabel"),
)
