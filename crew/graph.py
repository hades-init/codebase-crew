import logging

from langgraph.graph import START, END, StateGraph

from crew.core.github_client import TRIAGED_LABEL, has_label
from crew.nodes.commenter import comment
from crew.nodes.triager import classify
from crew.state import State

logger = logging.getLogger(__name__)


def route_entry(state: State):
    if has_label(state["issue_number"], TRIAGED_LABEL):
        logger.info("Already triaged, skipping")
        return "skip"
    return "classify"


def build_graph():
    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("comment", comment)

    # graph.add_edge(START, "classify")
    graph.add_conditional_edges(START, route_entry, {"classify": "classify", "skip": END})
    graph.add_edge("classify", "comment")
    graph.add_edge("comment", END)

    return graph.compile()
