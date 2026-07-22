from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Github
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""
    GIT_AUTHOR_NAME: str = "codebase-crew[bot]"
    GIT_AUTHOR_EMAIL: str = "crew-bot@users.noreply.github.com"

    # logs
    LOG_DIR: Path = PROJECT_ROOT / "logs"

    # workspace directory for local checkouts of repo
    WORKSPACE_DIR: Path = PROJECT_ROOT / "workspace"

    # local checkout of the target repo that git commands operate on
    @computed_field
    @property
    def REPO_PATH(self) -> Path:
        return self.WORKSPACE_DIR / self.GITHUB_REPO.split("/")[-1]

    # Model
    TRIAGER_MODEL: str = "claude-haiku-4-5"  # "claude-sonnet-4-6"
    PLANNER_MODEL: str = "claude-opus-4-8"
    CODER_MODEL: str = "claude-opus-4-8"
    REVIEWER_MODEL: str = "claude-opus-4-8"

    # max code revisions
    MAX_REVISIONS: int = 3

    # Sqlite DB for state persistance
    CHECKPOINT_DATABASE: Path = PROJECT_ROOT / "data/sqlite/checkpoints.sqlite"


settings = Settings()

for d in [settings.WORKSPACE_DIR, settings.LOG_DIR, settings.CHECKPOINT_DATABASE.parent]:
    d.mkdir(parents=True, exist_ok=True)
