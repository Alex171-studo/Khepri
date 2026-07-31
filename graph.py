from langchain.agents import create_agent
from tools import fetch_inventory, record_order
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langgraph.graph.message import MessagesState
from langchain.agents.middleware import wrap_tool_call
from agent_executor_prompt import system_prompt

memory = MemorySaver()
model = ChatOpenAI(model_name="gpt-5.4-mini", temperature=0.0)

@wrap_tool_call
def log_tool_calls(request, handler):
    call = request.tool_call
    print(f"  [middleware] calling {call['name']} with {call['args']}")
    return handler(request)

executive_agent = create_agent(
    tools=[fetch_inventory, record_order],
    system_prompt=system_prompt,
    model=model,
    middleware=[log_tool_calls],
    name="OrderAgent",
    state_schema=MessagesState,
    checkpointer=memory
)