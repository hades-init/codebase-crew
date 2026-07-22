from functools import cache
from enum import Enum

from github import Auth, Github
from github.Issue import Issue
from github.PullRequest import PullRequest

from crew.core.config import settings

auth = Auth.Token(settings.GITHUB_TOKEN)

gh = Github(auth=auth, lazy=True)


@cache
def _get_repo():
    return gh.get_repo(settings.GITHUB_REPO)


# issue labels
class IssueLabel(Enum):
    TRIAGED_LABEL = "triaged"
    PR_OPENED = "pr opened"
    NEEDS_HUMAN = "needs human"  # escalation


def get_issue(number: int) -> Issue:
    repo = _get_repo()
    return repo.get_issue(number)


def has_label(number: int, label: str) -> bool:
    """Return True if the issue carries the given label."""
    issue = get_issue(number)
    return any(l.name == label for l in issue.labels)


def create_pull_request(
    head: str, base: str, title: str, body: str, draft: bool = True
) -> PullRequest:
    """Open a pull request from `head` into `base`."""
    repo = _get_repo()
    return repo.create_pull(head=head, base=base, title=title, body=body, draft=draft)
