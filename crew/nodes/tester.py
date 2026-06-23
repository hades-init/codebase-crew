import logging

from crew.core.test_runner import run_tests
from crew.state import State

logger = logging.getLogger(__name__)


def run_test_suite(state: State) -> dict:
    """Run the full suite post-fix and judge success against the baseline failures.

    Success = the fix resolved at least one previously-failing test AND
    introduced no regressions. Pre-existing unrelated failures are ignored.
    """
    baseline = set(state.get("baseline_failures", []))
    result = run_tests()  # full suite against the coder's working tree
    after = set(result.failures)

    regressions = sorted(after - baseline)  # were passing, now failing -> bad
    resolved = sorted(baseline - after)  # were failing, now passing -> the fix
    still_failing = sorted(after & baseline)  # pre-existing, unrelated
    passed = not regressions and bool(resolved)

    report = (
        f"{result.summary}\n"
        f"resolved:      {resolved or 'none'}\n"
        f"regressions:   {regressions or 'none'}\n"
        f"pre-existing:  {still_failing or 'none'}"
    )
    logger.info(
        "Tester verdict: passed=%s, resolved=%s, regressions=%s", passed, resolved, regressions
    )
    return {
        "test_results": report,
        "tests_passed": passed,
        "messages": [
            {
                "node": "tester",
                "content": f"test results: tests_passed={passed}, resolved={resolved}, regressions={regressions}",
            }
        ],
    }
