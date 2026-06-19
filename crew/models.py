from typing import Literal

from pydantic import BaseModel, Field


class Classification(BaseModel):
    issue_type: Literal["bug", "feature", "invalid", "needs_info"] = Field(
        description="Type of issue."
    )
