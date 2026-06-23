from crew.core.github_client import IssueLabel, get_issue
from crew.state import State


def comment(state: State):
    issue = get_issue(state["issue_number"])
    issue_comment = issue.create_comment(f"Triage: {state['issue_type']}")
    issue.add_to_labels(IssueLabel.TRIAGED_LABEL.value)
    return {
        "messages": [
            {
                "node": "commenter",
                "content": f"comment created: id={issue_comment.id}, labels=[{IssueLabel.TRIAGED_LABEL.value}]",
            }
        ]
    }
