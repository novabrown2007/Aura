"""Outlook/Hotmail provider implementation for Aura email."""

from __future__ import annotations

from modules.email.models import EmailProviderType
from modules.email.providers.emailProvider import EmailProvider


class OutlookProvider(EmailProvider):
    """Deterministic Outlook-style provider."""

    providerType = EmailProviderType.OUTLOOK
