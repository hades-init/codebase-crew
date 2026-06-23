import logging

from crew.core.github_client import IssueLabel, create_pull_request, get_issue
from crew.core.workspace import GitRepo
from crew.state import State


logger = logging.getLogger(__name__)


PR_BODY_TEMPLATE = """Automated fix by the **Codebase Crew** 🤖

Fixed issue #{number}

## Plan
{plan}

## Test results
{test_results}
"""


def open_pr(state: State):
    repo = GitRepo(state["repo_path"])
    branch = state["branch_name"]
    issue_number = state["issue_number"]

    sha = repo.commit(message=f"Fix issue #{issue_number}: {state['issue_title']}")
    if sha is None:
        logger.warning("No changes to commit for issue #%d; skipping pull request", issue_number)
        return {
            "messages": [
                {"node": "open_pr", "content": "no changes to commit; pull request skipped"}
            ]
        }

    repo.push(branch)
    pull_request = create_pull_request(
        base=repo.default_branch,
        head=branch,
        title=f"Fix #{issue_number}: {state['issue_title']}",
        body=PR_BODY_TEMPLATE.format(
            number=issue_number, plan=state["plan"], test_results=state["test_results"]
        ),
        draft=True,
    )
    get_issue(issue_number).add_to_labels(IssueLabel.PR_OPENED.value)

    logger.info("Opened draft pull request: %s", pull_request.html_url)
    return {
        "pr_url": pull_request.html_url,
        "messages": [{"node": "open_pr", "content": f"Draft PR opened: {pull_request.html_url}"}],
    }
