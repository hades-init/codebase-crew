import logging

from langgraph.types import interrupt, Command

from crew.state import State

logger = logging.getLogger(__name__)


def human_gate(state: State) -> dict:
    """Pause for human approval before opening a PR. Carries the review context
    in the interrupt payload; the client renders it and supplies the answer."""

    answer = interrupt(
        {
            "issue_number": state["issue_number"],
            "issue_title": state["issue_title"],
            "branch_name": state["branch_name"],
            "diff": state["diff"],
            "test_results": state["test_results"],
            "prompt": "Open a draft PR for these changes? [y/N]",
        }
    )

    approved = str(answer).strip().lower() in ("y", "yes")
    logger.info("Human gate: approved=%s", approved)
    return {
        "approved": approved,
        "messages": [{"node": "human_gate", "content": f"human-in-the-loop: approved={approved}"}],
    }
