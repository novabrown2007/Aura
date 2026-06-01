"""Generic IMAP/SMTP provider implementation for Aura email."""

from __future__ import annotations

from modules.email.models import EmailProviderType
from modules.email.providers.emailProvider import EmailProvider


class ImapSmtpProvider(EmailProvider):
    """Deterministic IMAP/SMTP fallback provider."""

    providerType = EmailProviderType.IMAP_SMTP
