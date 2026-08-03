from pydantic import BaseModel, Field
from fastapi import FastAPI
from dotenv import load_dotenv
from graph import get_executive_agent
from contextlib import asynccontextmanager
import os
from langchain.messages import HumanMessage, SystemMessage
from agent_executor_prompt import prompt

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv(override=True)

class ChatMessageRequest(BaseModel):
    customer_phone: str = Field(description="Unique identifier of the customer (phone number)")
    message: str = Field(description="The text message sent by the customer")

class ChatMessageResponse(BaseModel):
    status:str = Field(default="success", description="Status of the message processing")
    response:str = Field(description="The generated response message")

executive_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global executive_agent
    db_uri = os.environ.get("DB_URL")

    async with AsyncConnectionPool(
        conninfo=db_uri,
        max_size=10,
        max_idle=300,
        check=AsyncConnectionPool.check_connection,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            }
    ) as pool:
        
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        executive_agent = get_executive_agent(checkpointer)
        print("✅ Executive agent initialized and ready to handle requests.")
        yield

    print("🛑 Superbase connection closed.")

app = FastAPI(
    title="Khepri Chat API",
    description="API for handling customer chat messages",
    lifespan=lifespan
)

@app.post("/chat/", response_model=ChatMessageResponse, summary="Handle incoming chat messages from customers")
async def respond_user_request(request:ChatMessageRequest) -> ChatMessageResponse:
    customer_phone = request.customer_phone
    message = request.message
    config = {"configurable":{"thread_id":customer_phone}}
    input_messages = prompt.format_messages(customer_phone=customer_phone, message=message)

    result = await executive_agent.ainvoke({"messages":input_messages}, config=config)  
    response = result["messages"][-1].content

    return ChatMessageResponse(response=response)