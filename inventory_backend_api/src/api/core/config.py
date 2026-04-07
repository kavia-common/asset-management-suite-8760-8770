from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Notes:
    - Do not hardcode secrets. Configure using environment variables.
    - The DB container provides MONGODB_URL and MONGODB_DB.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    node_env: str = Field(default="development", alias="NODE_ENV")

    # Network / CORS
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    allowed_methods: str = Field(default="*", alias="ALLOWED_METHODS")
    allowed_headers: str = Field(default="*", alias="ALLOWED_HEADERS")

    # Security / JWT
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_exp_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXP_MINUTES")

    # DB (Mongo)
    mongodb_url: str = Field(default="", alias="MONGODB_URL")
    mongodb_db: str = Field(default="", alias="MONGODB_DB")

    # App URLs (useful for docs / integration)
    backend_url: str = Field(default="", alias="BACKEND_URL")
    frontend_url: str = Field(default="", alias="FRONTEND_URL")


_settings: Settings | None = None


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Get singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
