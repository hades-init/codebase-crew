import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import Checkpointer

from crew.core.github_client import IssueLabel, has_label
from crew.nodes import (
    classify,
    comment,
    human_gate,
    open_pr,
    plan,
    review,
    run_test_suite,
    setup_workspace,
    write_code,
)
from crew.state import State


logger = logging.getLogger(__name__)


def route_entry(state: State) -> str:
    if has_label(state["issue_number"], IssueLabel.TRIAGED_LABEL.value):
        logger.info("Already triaged, skipping")
        return "skip"
    return "classify"


def route_by_type(state: State) -> str:
    return "fix" if state["issue_type"] == "bug" else "comment"


def route_after_test(state: State) -> str:
    return (
        "review" if state["tests_passed"] else END
    )  # add cycle back to coder; update condition with revision count


def route_after_review(state: State) -> str:
    return (
        "gate" if state["review_verdict"] == "approve" else END
    )  # add cycle back to coder; update condition with revision count


def route_after_gate(state: State) -> str:
    return "open_pr" if state["approved"] else END


def build_graph(checkpointer: Checkpointer = None):
    graph = StateGraph(State)

    graph.add_node("classify", classify)
    graph.add_node("comment", comment)
    graph.add_node("setup", setup_workspace)
    graph.add_node("plan", plan)
    graph.add_node("code", write_code)
    graph.add_node("test", run_test_suite)
    graph.add_node("review", review)
    graph.add_node("gate", human_gate)
    graph.add_node("open_pr", open_pr)

    graph.add_conditional_edges(START, route_entry, {"classify": "classify", "skip": END})
    graph.add_conditional_edges("classify", route_by_type, {"fix": "setup", "comment": "comment"})
    graph.add_edge("comment", END)

    graph.add_edge("setup", "plan")
    graph.add_edge("plan", "code")
    graph.add_edge("code", "test")
    graph.add_conditional_edges("test", route_after_test)
    graph.add_conditional_edges("review", route_after_review)
    graph.add_conditional_edges("gate", route_after_gate)
    graph.add_edge("open_pr", END)

    return graph.compile(checkpointer=checkpointer)
