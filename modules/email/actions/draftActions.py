"""Draft-specific email actions."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


DRAFT_ACTIONS = (
    ModuleAction(
        name="email.listDrafts",
        description="List saved drafts.",
        method="listDrafts",
        parameters={"accountId": {"type": "string"}},
        permissions=("email.draft",),
        capabilities=("email.draft",),
        target="listDrafts",
    ),
    ModuleAction(
        name="email.createDraft",
        description="Create a draft email.",
        method="createDraft",
        parameters={"accountId": {"type": "string"}, "to": {"type": "array"}, "subject": {"type": "string"}, "body": {"type": "string"}},
        permissions=("email.draft",),
        capabilities=("email.draft",),
        target="createDraft",
    ),
    ModuleAction(
        name="email.updateDraft",
        description="Update an existing draft.",
        method="updateDraft",
        parameters={"draftId": {"type": "string"}},
        requiredParameters=("draftId",),
        permissions=("email.draft",),
        capabilities=("email.draft",),
        target="updateDraft",
    ),
    ModuleAction(
        name="email.sendEmail",
        description="Send an email or draft.",
        method="sendEmail",
        parameters={"accountId": {"type": "string"}, "draftId": {"type": "string"}, "to": {"type": "array"}, "subject": {"type": "string"}, "body": {"type": "string"}},
        permissions=("email.send",),
        capabilities=("email.send",),
        safe=False,
        target="sendEmail",
    ),
    ModuleAction(
        name="email.scheduleEmail",
        description="Schedule an email for future send.",
        method="scheduleEmail",
        parameters={"accountId": {"type": "string"}, "draftId": {"type": "string"}, "sendAt": {"type": "string"}},
        requiredParameters=("sendAt",),
        permissions=("email.schedule",),
        capabilities=("email.schedule",),
        safe=False,
        target="scheduleEmail",
    ),
)
