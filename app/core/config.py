# app/config.py (or wherever your Settings class is)
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Arogya Sewa Backend APIs"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    APP_DOMAIN: str = Field(
        default="http://localhost:8000", description="API domain for callbacks"
    )

    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    # PostgreSQL settings (example)
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DB_HOST: str  # matches service name in docker-compose
    DB_PORT: int

    # Cloudinary settings
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # Khalti Payment Gateway settings
    KHALTI_SECRET_KEY: str = Field(
        ..., description="Khalti backend secret key (required)"
    )
    KHALTI_PUBLIC_KEY: str = Field(
        ..., description="Khalti frontend public key (required)"
    )
    KHALTI_API_URL: str = Field(
        default="https://dev.khalti.com/api/v2",
        description="Khalti API endpoint (default: sandbox)",
    )
    ADVANCE_PAYMENT_PERCENTAGE: float = Field(
        default=10.0, description="Advance payment percentage for appointments"
    )

    # --- SYNC engine (for Alembic and scripts)
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"

    # --- ASYNC engine (for FastAPI async endpoints)
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        # ✅ DO NOT include env_file=".env"
        case_sensitive=False,
        extra="ignore",
        # Pydantic will read from os.environ — which Docker already populated!
    )


settings = Settings()  # type: ignore
