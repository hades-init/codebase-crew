import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import Checkpointer

from crew.core.config import settings
from crew.core.github_client import IssueLabel, has_label, get_issue
from crew.nodes import (
    classify,
    comment,
    escalate,
    human_gate,
    open_pr,
    plan,
    reproduce,
    review,
    revise,
    run_test_suite,
    setup_workspace,
    write_code,
)
from crew.state import State


logger = logging.getLogger(__name__)


_TERMINAL = {
    IssueLabel.TRIAGED_LABEL.value,
    IssueLabel.PR_OPENED.value,
    IssueLabel.NEEDS_HUMAN.value,
}


def route_entry(state: State) -> str:
    labels = {l.name for l in get_issue(state["issue_number"]).labels}
    if labels & _TERMINAL:
        logger.info("Issue #%d already handled, skipping", state["issue_number"])
        return "skip"
    return "classify"


def route_by_type(state: State) -> str:
    return "fix" if state["issue_type"] == "bug" else "comment"


def route_after_reproduce(state: State) -> str:
    return "code" if state["reproduced"] else "escalate"


def route_after_test(state: State) -> str:
    if state["tests_passed"]:
        return "review"
    return "revise" if state["revision_count"] < settings.MAX_REVISIONS else "escalate"


def route_after_review(state: State) -> str:
    if state["review_verdict"] == "approve":
        return "gate"
    return "revise" if state["revision_count"] < settings.MAX_REVISIONS else "escalate"


def route_after_gate(state: State) -> str:
    return "open_pr" if state["approved"] else "end"


def build_graph(checkpointer: Checkpointer = None):
    graph = StateGraph(State)

    graph.add_node("classify", classify)
    graph.add_node("comment", comment)
    graph.add_node("setup", setup_workspace)
    graph.add_node("plan", plan)
    graph.add_node("reproduce", reproduce)
    graph.add_node("code", write_code)
    graph.add_node("test", run_test_suite)
    graph.add_node("review", review)
    graph.add_node("revise", revise)
    graph.add_node("gate", human_gate)
    graph.add_node("open_pr", open_pr)
    graph.add_node("escalate", escalate)

    graph.add_conditional_edges(START, route_entry, {"classify": "classify", "skip": END})
    graph.add_conditional_edges("classify", route_by_type, {"fix": "setup", "comment": "comment"})
    graph.add_edge("comment", END)

    graph.add_edge("setup", "plan")
    graph.add_edge("plan", "reproduce")
    graph.add_conditional_edges(
        "reproduce", route_after_reproduce, {"code": "code", "escalate": "escalate"}
    )
    graph.add_edge("code", "test")
    graph.add_conditional_edges(
        "test", route_after_test, {"review": "review", "revise": "revise", "escalate": "escalate"}
    )
    graph.add_conditional_edges(
        "review", route_after_review, {"gate": "gate", "revise": "revise", "escalate": "escalate"}
    )
    graph.add_edge("revise", "code")
    graph.add_conditional_edges("gate", route_after_gate, {"open_pr": "open_pr", "end": END})
    graph.add_edge("escalate", "comment")
    graph.add_edge("open_pr", END)

    return graph.compile(checkpointer=checkpointer)
