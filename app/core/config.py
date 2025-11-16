# app/config.py (or wherever your Settings class is)
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "My FastAPI App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 365

    # PostgreSQL settings (example)
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DB_HOST: str  # matches service name in docker-compose
    DB_PORT: int

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
