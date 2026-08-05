from langchain.agents import create_agent
from tools import fetch_inventory, create_checkout_session
from langchain_openai import ChatOpenAI
from langgraph.graph.message import MessagesState
from langchain.messages import ToolMessage
from langchain.agents.middleware import wrap_tool_call
from agent_executor_prompt import system_prompt

model = ChatOpenAI(model_name="gpt-5.4-mini", temperature=0.3)

@wrap_tool_call
async def log_tool_calls(request, handler):
    call = request.tool_call
    print(f"  [middleware] calling {call['name']} with {call['args']}")
    try:
        return await handler(request)
    except Exception as e:
        print(f"  [middleware] error calling {call['name']}: {e}")
        return f"Erreur lors de l'exécution de l'outil {call['name']}: {str(e)}"

def get_executive_agent(checkpointer):

    return create_agent(
        tools=[fetch_inventory, create_checkout_session],
        system_prompt=system_prompt,
        model=model,
        middleware=[log_tool_calls],
        name="OrderAgent",
        state_schema=MessagesState,
        checkpointer=checkpointer
    )