from pydantic import BaseModel, Field
from fastapi import FastAPI
from dotenv import load_dotenv
from graph import executive_agent
from langchain.messages import HumanMessage, SystemMessage

load_dotenv(override=True)

class ChatMessageRequest(BaseModel):
    customer_phone: str = Field(description="Unique identifier of the customer (phone number)")
    message: str = Field(description="The text message sent by the customer")

class ChatMessageResponse(BaseModel):
    status:str = Field(default="success", description="Status of the message processing")
    response:str = Field(description="The generated response message")

app = FastAPI(
    title="Khepri Chat API",
    description="API for handling customer chat messages",
)

@app.post("/chat/", response_model=ChatMessageResponse, summary="Handle incoming chat messages from customers")
def respond_user_request(request:ChatMessageRequest) -> ChatMessageResponse:
    customer_phone = request.customer_phone
    message = request.message
    config = {"configurable":{"thread_id":customer_phone}}
    input_messages = [
        SystemMessage(content=f"[CONTEXTE WHATSAPP] Numéro client vérifié : {customer_phone}"),
        HumanMessage(content=message)
        ]
    result = executive_agent.invoke({"messages":input_messages}, config=config)  
    response = result["messages"][-1].content
    return ChatMessageResponse(response=response)