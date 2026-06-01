"""Aura unified email capability module."""

from __future__ import annotations

from modules.email.emailModule import EmailModule

MODULE_METADATA = EmailModule.metadata


def createModule(context=None):
    """Create the Aura email module."""

    return EmailModule(context)


def register(context):
    """Register the email module on the runtime context."""

    context.email = EmailModule(context)


__all__ = [
    "EmailModule",
    "MODULE_METADATA",
    "createModule",
    "register",
]
