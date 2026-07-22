import logging

from crew.state import State


logger = logging.getLogger(__name__)


def revise(state: State) -> dict:
    """Bump the revision counter before looping back to the coder."""
    count = state.get("revision_count", 0) + 1
    reason = "tests failing" if not state.get("tests_passed") else "review rejected"
    logger.info("Revision #%d requested (%s)", count, reason)
    return {
        "revision_count": count,
        "messages": [{"node": "revise", "content": f"revision #{count}: reason={reason}"}],
    }
