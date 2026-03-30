import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.core.config import settings

if TYPE_CHECKING:
    from app.modules.email.v1.mailgun_service import MailgunGateway

logger = logging.getLogger(__name__)


class MailgunConfig:
    """Mailgun configuration with startup validation helpers."""

    ENABLED: bool = settings.MAILGUN_ENABLED
    API_KEY: str | None = settings.MAILGUN_API_KEY
    DOMAIN: str | None = settings.MAILGUN_DOMAIN
    BASE_URL: str = settings.MAILGUN_BASE_URL
    FROM_EMAIL: str = settings.MAILGUN_FROM_EMAIL
    WEBHOOK_SIGNING_KEY: str | None = settings.MAILGUN_WEBHOOK_SIGNING_KEY
    TIMEOUT_SECONDS: float = settings.MAILGUN_TIMEOUT_SECONDS

    @classmethod
    def validate_config(cls) -> None:
        """Validate Mailgun configuration when the feature is enabled."""
        if not cls.ENABLED:
            logger.info("Mailgun integration is disabled")
            return

        if not cls.API_KEY:
            raise RuntimeError("MAILGUN_API_KEY is required when MAILGUN_ENABLED=true")
        if not cls.DOMAIN:
            raise RuntimeError("MAILGUN_DOMAIN is required when MAILGUN_ENABLED=true")
        if not cls.WEBHOOK_SIGNING_KEY:
            raise RuntimeError(
                "MAILGUN_WEBHOOK_SIGNING_KEY is required when MAILGUN_ENABLED=true"
            )

        logger.info("Mailgun configured for domain: %s", cls.DOMAIN)


def init_mailgun() -> None:
    """Initialize and validate Mailgun configuration."""
    MailgunConfig.validate_config()


def get_mailgun_service() -> "MailgunGateway":
    from app.modules.email.v1.mailgun_service import HttpxMailgunGateway

    if not settings.MAILGUN_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mailgun integration is disabled",
        )

    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mailgun is not configured correctly",
        )

    if not settings.MAILGUN_WEBHOOK_SIGNING_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mailgun webhook signing key is missing",
        )

    return HttpxMailgunGateway(
        api_key=settings.MAILGUN_API_KEY,
        domain=settings.MAILGUN_DOMAIN,
        base_url=settings.MAILGUN_BASE_URL,
        from_email=settings.MAILGUN_FROM_EMAIL,
        webhook_signing_key=settings.MAILGUN_WEBHOOK_SIGNING_KEY,
        timeout_seconds=settings.MAILGUN_TIMEOUT_SECONDS,
    )
