from functools import cache

from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from crew.core.config import settings
from crew.models import Classification
from crew.state import State

load_dotenv()


SYSTEM_PROMPT = """You are the triage agent for a software project's issue tracker.
Classify each incoming GitHub issue into exactly one issue type:

- "bug": existing behavior is broken or wrong — crashes, incorrect output, or behavior
  that contradicts what the code/docs promise.
- "feature": a request for new functionality, or an enhancement to behavior that already
  works correctly.
- "needs_info": plausibly actionable, but missing the details needed to act — no
  reproduction steps, no expected-vs-actual, or ambiguous scope.
- "invalid": not actionable — spam, off-topic, a duplicate, or a pure question that implies
  no change.

Judge only from the title and body provided. If something is described as not working as
documented, prefer "bug". If key reproduction details are absent, prefer "needs_info"."""


@cache
def _get_client() -> ChatAnthropic:
    return ChatAnthropic(model=settings.TRIAGER_MODEL, max_tokens=512)  # type: ignore[call-arg]


def classify(state: State) -> dict:
    llm = _get_client()
    user_content = (
        f"Issue #{state['issue_number']}: {state['issue_title']}\n\n{state['issue_body']}"
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    result = llm.with_structured_output(Classification).invoke(messages)

    return {
        "issue_type": result.issue_type,  # type: ignore[union-attr]
        "messages": [
            {
                "node": "triager",
                "content": f"classification: issue_type={result.issue_type}",  # type: ignore[union-attr]
            }
        ],
    }
