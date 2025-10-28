from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "My FastAPI App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # DATABASE_URL: str
       # Security settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY", min_length=32, description="Secret key for JWT token generation")

    ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 365
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
