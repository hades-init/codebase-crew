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
from crew.core.test_runner import run_tests
from crew.state import State


load_dotenv()

logger = logging.getLogger(__name__)

_TOOLS = [
    file_tools.read_file,
    file_tools.list_dir,
    file_tools.search,
    file_tools.write_test_file,
    file_tools.edit_test_file,
]

SYSTEM_PROMPT = """You are the test-writing agent in an automated bug-fixing crew.

Given a bug report and the planner's analysis, write exactly ONE regression test that
reproduces/captures the bug. The test MUST fail against the current (unfixed) code and would pass
once the bug is fixed.

Rules:
- Strictly DO NOT attempt to fix the bug or modify any non-test source file.
- Add the test to the suite under `tests/`, matching the project's pytest style, naming,
  and imports. Prefer adding a function to an existing test file when one fits.
- Assert the CORRECT expected behavior, so the test fails now and passes after the fix.
- Keep it minimal and focused on the given single reported issue.

When the test is written, briefly describe what you added, then stop."""


@cache
def _get_client() -> ChatAnthropic:
    return ChatAnthropic(model=settings.CODER_MODEL, max_tokens=8192)  # type: ignore[call-arg]


def _create_agent(model: BaseChatModel, recursion_limit: int = 25):
    return create_agent(
        model,
        tools=_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    ).with_config({"recursion_limit": recursion_limit})


@traceable(name="reproduce", run_type="chain")
def reproduce(state: State) -> dict:
    user_content = (
        f"Issue #{state['issue_number']}: {state['issue_title']}\n{state['issue_body']}\n\n"
        f"## Planner analysis:\n{state['plan']}\n\n"
        f"Target files: {', '.join(state['target_files'])}"
    )
    agent = _create_agent(_get_client())
    response = agent.invoke({"messages": [HumanMessage(content=user_content)]})
    print(response["messages"][-1])
    before = set(state.get("baseline_failures", []))
    after = set(run_tests().failures)
    new_failures = after - before
    reproduced = bool(new_failures)

    logger.info(
        "Reproduce bug: reproduced=%s, %d new failing test(s): %s",
        reproduced,
        len(new_failures),
        new_failures,
    )

    return {
        "baseline_failures": after,
        "reproduced": reproduced,
        "messages": [
            {
                "node": "reproduce",
                "content": f"bug reproduced={reproduced}, new_failures={new_failures}",
            }
        ],
    }
