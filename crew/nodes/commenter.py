from crew.core.github_client import TRIAGED_LABEL, get_issue
from crew.state import State


def comment(state: State):
    issue = get_issue(state["issue_number"])
    issue_comment = issue.create_comment(f"Triage: {state['issue_type']}")
    issue.add_to_labels(TRIAGED_LABEL)
    return {
        "messages": [
            {
                "node": "commenter",
                "content": f"Comment created (id={issue_comment.id}), labels=[{TRIAGED_LABEL}])",
            }
        ]
    }
