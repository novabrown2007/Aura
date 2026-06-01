"""Gmail provider implementation for Aura email."""

from __future__ import annotations

from modules.email.models import EmailProviderType
from modules.email.providers.emailProvider import EmailProvider


class GmailProvider(EmailProvider):
    """Deterministic Gmail-style provider."""

    providerType = EmailProviderType.GMAIL
