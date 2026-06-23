import operator
from typing import Annotated, Literal, TypedDict


class State(TypedDict):
    issue_number: int
    issue_title: str
    issue_body: str
    issue_type: Literal["bug", "feature", "invalid", "needs_info"]

    repo_path: str
    branch_name: str
    baseline_failures: list[str]

    plan: str
    target_files: list[str]

    diff: str

    test_results: str
    tests_passed: bool

    review_verdict: Literal["approve", "reject"]
    review_feedback: str
    revision_count: int  # circuit breaker for agent loop

    pr_url: str
    approved: bool

    messages: Annotated[list, operator.add]
