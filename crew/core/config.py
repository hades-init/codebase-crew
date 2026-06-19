from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    LOG_DIR: Path = PROJECT_ROOT / "logs"

    # Github
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""

    # Model
    TRIAGER_MODEL: str = "claude-haiku-4-5"


settings = Settings()

for d in [settings.LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)
