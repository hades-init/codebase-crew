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
from crew.models import Plan
from crew.state import State


load_dotenv()

logger = logging.getLogger(__name__)

_TOOLS = [file_tools.read_file, file_tools.list_dir, file_tools.search]
_MAX_TOOL_ITERS = 10


SYSTEM_PROMPT = """You are the planning agent in an automated bug-fixing crew.

You are given a GitHub bug report/issue. Investigate the repository using the provided
tools (list_files, search, read_file) to find the root cause, then produce a concrete
bug fix plan for a separate coding agent.

Guidelines:
- Explore before concluding: locate the relevant file(s) and read the actual code.
- Identify the *root cause*, not just the symptom.
- The plan must name exact target files and give precise, ordered steps.
- Do NOT write code or modify files — planning only. The coder implements your plan.
- Keep the fix minimal and focused only on the reported issue.

When you understand the problem, stop calling tools and state your conclusion."""


@cache
def _get_client() -> ChatAnthropic:
    return ChatAnthropic(model=settings.PLANNER_MODEL, max_tokens=4096)  # type: ignore[call-arg]


def _create_agent(model: BaseChatModel, recursion_limit: int = 25):
    return create_agent(
        model,
        tools=_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=Plan,
    ).with_config({"recursion_limit": recursion_limit})


@traceable(name="planner", run_type="chain")
def plan(state: State) -> dict:
    agent = _create_agent(_get_client())
    response = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=f"Issue #{state['issue_number']}: {state['issue_title']}\n\n{state['issue_body']}"
                )
            ]
        }
    )
    plan: Plan = response["structured_response"]

    plan_details = f"{plan.summary}\n\nSteps to fix the issue:\n" + "\n".join(
        f"{i}. {s}" for i, s in enumerate(plan.steps, 1)
    )
    logger.info("Planner target files: %s \n\nSteps:\n%s", plan.target_files, plan.steps)
    return {
        "plan": plan_details,
        "target_files": plan.target_files,
        "messages": [
            {
                "node": "planner",
                "content": f"plan: summary={plan.summary}, target_files={plan.target_files}",
            }
        ],
    }
