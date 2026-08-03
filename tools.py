from langchain.tools import tool
from dotenv import load_dotenv
import os
from pyairtable import Api
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
import asyncio
from schemas.checkout import CheckoutRequest, CheckoutResponse, CheckoutErrorResponse, CheckoutErrorCode, purchase_item
import httpx
from typing import Union

load_dotenv(override=True)

N8N_CHECKOUT_WEBHOOK_URL = os.getenv("N8N_CHECKOUT_WEBHOOK_URL")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

COLLECTION_NAME = "khepri_products"
MODEL_NAME = "text-embedding-3-small"

embeddings = OpenAIEmbeddings(model=MODEL_NAME)
qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
    cloud_inference=True
)

airtable = Api(AIRTABLE_API_KEY)
stocks_table = airtable.table(AIRTABLE_BASE_ID, "Stocks")

class Product(BaseModel):
    name: str = Field(description="Name of the product")
    product_id: str = Field(description="Unique identifier of the product")
    stock_quantity: int = Field(description="Available quantity of the product in stock")
    price: float = Field(description="Price of the product")
    description: str = Field(description="Description of the product")

@tool
async def create_checkout_session(
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    items: list[purchase_item]
    
) -> Union[CheckoutResponse, CheckoutErrorResponse]:
    """
    Create a checkout session for the customer.

    This tool is called after the customer has confirmed their order and provided their details.

    Arguments:
    - customer_name: The full name of the customer.
    - customer_phone: The phone number of the customer.
    - delivery_address: The delivery address for the order.
    - items: A list of items being purchased, each containing the product_id and quantity (eg. [{"product_id": "prod_123", "quantity": 2}, {"product_id": "prod_456", "quantity": 1}]).

    Returns:
    - CheckoutResponse: If the checkout session is created successfully.
    - CheckoutErrorResponse: If there is an error during the checkout process.
    """
    request = CheckoutRequest(
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        items=items
        
    )

    try:
       async with httpx.AsyncClient() as client:
            response = await client.post(N8N_CHECKOUT_WEBHOOK_URL, json=request.model_dump(), timeout=30.0)
            data = response.json()
            if data.get("success") is False:
                return CheckoutErrorResponse(**data)
            return CheckoutResponse(**data)
    
    except httpx.TimeoutException:
        return CheckoutErrorResponse(
            success=False,
            error_code=CheckoutErrorCode.PAYMENT_PROVIDER_DOWN,
            reason="The payment provider is currently down. Please try again later."
        )
    except httpx.RequestError as e:
        return CheckoutErrorResponse(
            success=False,
            error_code=CheckoutErrorCode.UNKNOWN_ERROR,
            reason=f"An error occurred while creating the checkout session: {str(e)}"
        )
       


@tool
async def fetch_inventory(query:str="") -> list[Product]:
    """
    Search the product catalog.

    Call this tool whenever the user:
    - asks about a product,
    - asks for a price,
    - asks about stock or availability,
    - asks for product information,
    - asks to see the catalog or available products.

    Arguments:
    - query:
        - If the user mentions a product or describes one, pass that text.
        - If the user asks to see all available products (e.g. "Quels produits avez-vous ?", "Montrez-moi votre catalogue"), pass an empty string "".

    Returns:
    Up to three matching products (or the first products in the catalog when query is empty), including their internal product_id, name, description, price and available stock.

    Never invent product information. Always rely on this tool.
    """

    matched_products = []
    records = []

    if query:
        query = query.lower().strip()

        embedded_query = embeddings.embed_query(query)
        results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=embedded_query,
            limit=3
        )

        if not results.points:
            return []

        points = results.points

        for point in points:
            airtable_record_id = point.payload.get("airtable_id")

            if not airtable_record_id:
                continue

            record = await asyncio.to_thread(stocks_table.get, airtable_record_id)
            if not record:
                continue
            records.append(record)

    else:
        records = await asyncio.to_thread(stocks_table.all, max_records=10)
    
    for record in records:
        fields = record['fields']
        product = Product(
            name=fields.get('name', ''),
            product_id=record.get('id', ''),
            stock_quantity=int(fields.get('stock_quantity', 0)),
            price=float(fields.get('price', 0.0)),
            description=fields.get('description', '')
        )
        matched_products.append(product)

    return matched_products

