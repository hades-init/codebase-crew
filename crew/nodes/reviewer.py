from functools import cache
import logging

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from crew.core import file_tools
from crew.core.config import settings
from crew.models import Review
from crew.state import State


load_dotenv()

logger = logging.getLogger(__name__)

_TOOLS = [file_tools.read_file, file_tools.search]

SYSTEM_PROMPT = """You are the code reviewing agent in an automated bug-fixing crew.

You are given the original bug report/issue, the structured fix plan, the unified diff the coder
produced, and the test results. Decide whether this change should be opened as a pull request.

Use the read-only tools (read_file, search) to inspect the changed files in full context
before judging — a diff alone hides the surrounding code.

Approve only if ALL of these hold:
- The change fixes the root cause in the issue, not just the symptom.
- It is minimal and focused — no unrelated edits, dead code, or reformatting.
- Tests pass with no regressions, AND the fix is covered by a meaningful test. 
  For a latent bug, a regression test that would fail on the OLD code must have been added.
- The code matches the surrounding style and conventions.

Otherwise reject with specific, actionable feedback the coder should act on (name the files and
what to change). Do not rewrite the code yourself — plan/critique only."""


@cache
def _get_client() -> ChatAnthropic:
    return ChatAnthropic(model=settings.REVIEWER_MODEL, max_tokens=8192)  # type: ignore[call-arg]


def _create_agent(model: BaseChatModel, recursion_limit: int = 25):
    return create_agent(
        model,
        tools=_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=Review,
    ).with_config({"recursion_limit": recursion_limit})


@traceable(name="reviewer", run_type="chain")
def review(state: State) -> dict:
    user_content = (
        f"Issue #{state['issue_number']}: {state['issue_title']}\n\n{state['issue_body']}\n\n"
        f"## Plan\n{state['plan']}\n\n"
        f"## Diff\n{state['diff']}\n\n"
        f"## Test results\n{state['test_results']}"
    )

    agent = _create_agent(_get_client())
    response = agent.invoke({"messages": [HumanMessage(content=user_content)]})
    review: Review = response["structured_response"]

    logger.info("Reviewer: verdict=%s, feedback: %s", review.verdict, review.feedback)
    return {
        "review_verdict": review.verdict,
        "review_feedback": review.feedback,
        "messages": [
            {
                "node": "reviewer",
                "content": f"review: verdict={review.verdict}, feedback={review.feedback[:200]} ... (truncated)",
            }
        ],
    }
