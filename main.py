from pydantic import BaseModel, Field
from fastapi import FastAPI
from dotenv import load_dotenv
from graph import get_executive_agent
from contextlib import asynccontextmanager
import os
from langchain_core.messages import HumanMessage
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from tools import http_client
import asyncio
from sync import start_sync_loop

load_dotenv(override=True)

class ChatMessageRequest(BaseModel):
    customer_phone: str = Field(description="Unique identifier of the customer (phone number)")
    message: str = Field(description="The text message sent by the customer")

class ChatMessageResponse(BaseModel):
    status:str = Field(default="success", description="Status of the message processing")
    response:str = Field(description="The generated response message")


SYNC_SECRET=os.environ.get("SYNC_SECRET")

executive_agent = None
sync_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global executive_agent
    global sync_task
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

        sync_task = asyncio.create_task(start_sync_loop())
        print("✅ Airtable sync service started.")

        yield

    if sync_task:
        sync_task.cancel()

        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    
    await http_client.aclose()
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

    result = await executive_agent.ainvoke({"messages": [HumanMessage(content=message)]}, config=config)  
    response = result["messages"][-1].content

    return ChatMessageResponse(response=response)

