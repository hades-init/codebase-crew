import logging

from crew.core.github_client import IssueLabel
from crew.state import State


logger = logging.getLogger(__name__)


def escalate(state: State) -> dict:
    if not state.get("reproduced", True):
        feedback = "Could not write a regression test that reproduces the issue."
    elif not state.get("tests_passed", True):
        feedback = state.get("test_results", "Tests keep failing")
    else:
        feedback = state.get("review_feedback", "No fix approved by reviewer.")
        
    comment = (
        f"🤖 The Codebase Crew could not produce an approved, passing fix after "
        f"{state.get('revision_count', 0)} revision(s). This issue needs human attention.\n\n"
        f"**Last feedback:**\n{feedback}"
    )

    logger.warning(
        "Escalated issue #%d after %d revision(s)",
        state["issue_number"],
        state.get("revision_count", 0),
    )
    return {
        "comment": comment,
        "labels": [IssueLabel.NEEDS_HUMAN.value],
        "messages": [
            {
                "node": "escalate",
                "content": f"escalation: issue #{state['issue_number']} needs human attention",
            }
        ],
    }
