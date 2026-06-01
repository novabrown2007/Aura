"""Label and tag email actions."""

from __future__ import annotations

from core.modules.base.moduleAction import ModuleAction


LABEL_ACTIONS = (
    ModuleAction(
        name="email.listLabels",
        description="List account labels and tags.",
        method="listLabels",
        parameters={"accountId": {"type": "string"}},
        permissions=("email.label",),
        capabilities=("email.labels",),
        target="listLabels",
    ),
    ModuleAction(
        name="email.applyLabel",
        description="Apply a label to a message.",
        method="applyLabel",
        parameters={"accountId": {"type": "string"}, "messageId": {"type": "string"}, "label": {"type": "string"}},
        requiredParameters=("messageId", "label"),
        permissions=("email.label",),
        capabilities=("email.labels",),
        target="applyLabel",
    ),
)
