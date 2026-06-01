"""Schedule-related email actions."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


SCHEDULE_EMAIL_ACTIONS = (
    ModuleAction(
        name="email.scheduleEmail",
        description="Schedule email delivery later.",
        method="scheduleEmail",
        parameters={"accountId": {"type": "string"}, "draftId": {"type": "string"}, "sendAt": {"type": "string"}},
        requiredParameters=("sendAt",),
        permissions=("email.schedule",),
        capabilities=("email.schedule",),
        safe=False,
        target="scheduleEmail",
    ),
)
