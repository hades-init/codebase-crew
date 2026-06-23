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
from crew.core.workspace import GitRepo
from crew.state import State


load_dotenv()

logger = logging.getLogger(__name__)

_TOOLS = [file_tools.read_file, file_tools.write_file, file_tools.edit_file]

SYSTEM_PROMPT = """You are the coding agent in an automated bug-fixing crew.

You are given a fix plan from the planner. Implement it in the repository using the provided tools:
- read_file: inspect a file before editing it.
- edit_file: replace an exact, unique snippet (preferred for surgical changes).
- write_file: overwrite or create a whole file.

Guidelines:
- Always read a file immediately before editing it, so your `old` snippet matches exactly.
- Make the smallest change that fixes the root cause described in the plan.
- Do not fix unrelated issues, reformat files, or touch tests unless the plan says so.
- After applying all changes, briefly state what you changed, then stop."""


@cache
def _get_client() -> ChatAnthropic:
    return ChatAnthropic(model=settings.CODER_MODEL, max_tokens=8192)  # type: ignore[call-arg]


def _create_agent(model: BaseChatModel, recursion_limit: int = 25):
    return create_agent(
        model,
        tools=_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    ).with_config({"recursion_limit": recursion_limit})


@traceable(name="coder", run_type="chain")
def write_code(state: State) -> dict:
    user_content = (
        f"Issue #{state['issue_number']}: {state['issue_title']}\n\n"
        f"Fix plan:\n{state['plan']}\n\n"
        f"Target files: {', '.join(state['target_files'])}"
    )

    agent = _create_agent(_get_client())
    response = agent.invoke({"messages": [HumanMessage(content=user_content)]})

    change = GitRepo(state["repo_path"]).diff()
    logger.info("Coder produced a diff of %d chars", len(change))
    return {
        "diff": change,
        "messages": [{"node": "coder", "content": f"applied changes: diff={len(change)} chars"}],
    }
