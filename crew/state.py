import operator
from typing import Annotated, Literal, TypedDict


class State(TypedDict):
    issue_number: int
    issue_title: str
    issue_body: str
    issue_type: Literal["bug", "feature", "invalid", "needs_info"]
    # plan: str
    # target_files: list[str]
    # branch_name: str
    # diff: str
    # test_results: str
    # review_verdict: Literal["approve", "reject"]
    # review_feedback: str
    # revision_count: int   # circuit breaker for agent loop
    messages: Annotated[list, operator.add]
    # pr_url: str
