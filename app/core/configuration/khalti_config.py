import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class KhaltiConfig:
    """Khalti Payment Gateway Configuration"""

    API_URL: str = settings.KHALTI_API_URL
    SECRET_KEY: str = settings.KHALTI_SECRET_KEY
    PUBLIC_KEY: str = settings.KHALTI_PUBLIC_KEY

    @classmethod
    def get_headers(cls) -> dict:
        """Get headers with Khalti authorization"""
        return {
            "Authorization": f"Key {cls.SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @classmethod
    def validate_config(cls) -> None:
        """Validate Khalti configuration on startup"""
        if not cls.SECRET_KEY:
            raise RuntimeError("KHALTI_SECRET_KEY not configured")
        if not cls.PUBLIC_KEY:
            raise RuntimeError("KHALTI_PUBLIC_KEY not configured")
        if not cls.API_URL:
            raise RuntimeError("KHALTI_API_URL not configured")

        logger.info(
            f"Khalti Payment Gateway configured - API: {cls.API_URL.split('/api/')[0]}"
        )


def init_khalti():
    """Initialize and validate Khalti configuration"""
    try:
        KhaltiConfig.validate_config()
        logger.info("Khalti Payment Gateway initialized successfully")
    except Exception as e:
        logger.error(f"Khalti initialization error: {e}")
        raise
