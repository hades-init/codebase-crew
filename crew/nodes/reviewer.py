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

_TOOLS = [file_tools.read_file]

SYSTEM_PROMPT = """You are a code review agent.
You are given a GitHub bug report/issue, the fix plan, fixed code diff and test results.
Review the code changes give your review - feedback and final verdict 
using only the structured output format"""


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
        f"Fix plan:\n{state['plan']}\n\n"
        f"Git diff:\n{state['diff']}\n\n"
        f"Test results:\n{state['test_results']}"
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
