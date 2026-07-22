from crew.core.github_client import IssueLabel, get_issue
from crew.state import State


def comment(state: State):
    issue = get_issue(state["issue_number"])
    issue_comment = issue.create_comment(state["comment"])
    issue.add_to_labels(*state["labels"])
    return {
        "messages": [
            {
                "node": "commenter",
                "content": f"comment created: id={issue_comment.id}, labels={state['labels']}",
            }
        ]
    }
