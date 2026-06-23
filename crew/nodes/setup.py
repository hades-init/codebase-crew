import logging

from crew.core.test_runner import run_tests
from crew.core.workspace import init_workspace
from crew.state import State

logger = logging.getLogger(__name__)


def setup_workspace(state: State) -> dict:
    """Clone/refresh the repo, branch for the issue, and record baseline failures.

    The baseline is the set of tests already failing on a clean checkout before
    the coder touches anything — the tester diffs against it to tell a real fix
    from pre-existing, unrelated breakage.
    """
    repo, branch = init_workspace(state["issue_number"])
    baseline = run_tests(repo.repo_path).failures
    logger.info("Workspace ready on %s; %d baseline failure(s)", branch, len(baseline))
    return {
        "repo_path": str(repo.repo_path),
        "branch_name": branch,
        "baseline_failures": baseline,
        "messages": [
            {
                "node": "setup",
                "content": f"workspace initialized: branch={branch}, baseline_failures={baseline}",
            }
        ],
    }
