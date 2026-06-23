import logging

from langgraph.types import interrupt, Command

from crew.state import State

logger = logging.getLogger(__name__)


def human_gate(state: State) -> dict:
    """Show the proposed changes + test results and ask human to approve a pull request."""
    print("\n" + "=" * 72)
    print(f"Issue #{state['issue_number']}: {state['issue_title']}")
    print(f"Branch: {state['branch_name']}")
    print("-" * 72 + "\nDIFF:\n")
    print(state["diff"] or "(empty)")
    print("-" * 72 + "\nTEST RESULTS:\n")
    print(state["test_results"])
    print("=" * 72)

    approved = interrupt("Open a draft PR for these changes? [y/N] ").strip().lower() in (
        "y",
        "yes",
    )
    logger.info("Human gate: approved=%s", approved)
    return {
        "approved": approved,
        "messages": [{"node": "human_gate", "content": f"human-in-the-loop: approved={approved}"}],
    }
