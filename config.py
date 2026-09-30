from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitBuddy – AI Fitness Plan Generator"

    gemini_api_key: str | None = None

    workout_model: str = "gemini-3.8-flash"

    tip_model: str = "gemini-3.8-flash"

    database_url: str = "sqlite:///./fitbuddy.db"

    admin_key: str = "change-this-admin-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()