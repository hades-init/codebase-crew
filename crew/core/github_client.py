from github import Auth, Github
from github.Issue import Issue

from crew.core.config import settings

auth = Auth.Token(settings.GITHUB_TOKEN)

gh = Github(auth=auth, lazy=True)

repo = gh.get_repo(settings.GITHUB_REPO)


def get_issue(number: int) -> Issue:
    return repo.get_issue(number)


TRIAGED_LABEL = "triaged"


def has_label(number: int, label: str) -> bool:
    """Return True if the issue carries the given label."""
    issue = get_issue(number)
    return any(l.name == label for l in issue.labels)
