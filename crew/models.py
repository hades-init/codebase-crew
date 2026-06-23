from typing import Literal

from pydantic import BaseModel, Field


class Classification(BaseModel):
    issue_type: Literal["bug", "feature", "invalid", "needs_info"] = Field(
        description="Type of issue."
    )


class Plan(BaseModel):
    summary: str = Field(
        description="Root cause analysis and the fix approach, in a brief and concise paragraph."
    )
    target_files: list[str] = Field(
        description="Repo-relative paths of target files that must change."
    )
    steps: list[str] = Field(
        description="Sequence of concrete steps for the coder to follow to fix the issue."
    )


class Review(BaseModel):
    verdict: Literal["approve", "reject"]
    feedback: str
