import argparse
import logging
from typing import cast

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


def main() -> None:
    setup_logging()
    args = parse_args()

    logger.info("Fetching issue #%d", args.issue)
    issue = get_issue(args.issue)

    graph = build_graph()
    result = graph.invoke(
        cast(
            State,
            {
                "issue_number": issue.number,
                "issue_title": issue.title,
                "issue_body": issue.body,
            },
        )
    )

    logger.info("Done. Issue #%d: {issue_type: %s}", issue.number, result.get("issue_type"))


if __name__ == "__main__":
    main()
