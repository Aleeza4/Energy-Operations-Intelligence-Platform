from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Energy Operations Intelligence Platform"
    app_env: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")
    random_seed: int = Field(default=42)

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "energy_operations"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    @property
    def config_file(self) -> Path:
        """Return the YAML configuration file for the active environment."""
        return PROJECT_ROOT / "configs" / f"{self.app_env}.yaml"

    def load_yaml_config(self) -> dict[str, Any]:
        """Load environment-specific YAML configuration."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        with self.config_file.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        if not isinstance(config, dict):
            raise ValueError("The YAML configuration must contain a mapping.")

        return config


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings()
