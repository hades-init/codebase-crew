from langchain import agents
from langchain.chat_models import BaseChatModel


def create_agent(
    model: BaseChatModel,
    tools=None,
    system_prompt=None,
    response_format=None,
    recursion_limit: int = 25,
):
    return agents.create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        response_format=response_format,
    ).with_config({"recursion_limit": recursion_limit})
