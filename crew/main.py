import argparse
import logging
from typing import cast

from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver

from crew.core.db import get_conn
from crew.core.github_client import get_issue
from crew.core.logging import setup_logging
from crew.graph import build_graph
from crew.state import State

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="crew",
        description="Run the codebase crew against a GitHub issue.",
    )
    parser.add_argument(
        "--issue",
        type=int,
        required=True,
        help="The GitHub issue number to process.",
    )
    return parser.parse_args()


def _render_gate(payload: dict) -> None:
    print("\n" + "=" * 72)
    print(f"Issue #{payload['issue_number']}: {payload['issue_title']}")
    print(f"Branch: {payload['branch_name']}")
    print("-" * 72 + "\nDIFF:\n")
    print(payload["diff"] or "(empty)")
    print("-" * 72 + "\nTEST RESULTS:\n")
    print(payload["test_results"])
    print("=" * 72)


def main() -> None:
    setup_logging()
    args = parse_args()

    logger.info("Fetching issue #%d", args.issue)
    issue = get_issue(args.issue)

    conn = get_conn()
    checkpointer = SqliteSaver(conn)

    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": f"issue-{issue.number}"}}

    result = graph.invoke(
        cast(
            State,
            {
                "issue_number": issue.number,
                "issue_title": issue.title,
                "issue_body": issue.body,
            },
        ),
        config=config,  # type: ignore[call-type]
    )

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        _render_gate(payload)
        answer = input(f"\n{payload['prompt']}: ")
        result = graph.invoke(Command(resume=answer), config=config)  # type: ignore[arg-type]

    logger.info(
        "Done. Issue #%d type=%s tests_passed=%s pr_url=%s",
        issue.number,
        result.get("issue_type"),
        result.get("tests_passed"),
        result.get("pr_url"),
    )


if __name__ == "__main__":
    main()
