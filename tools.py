from langchain.tools import tool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from qdrant_client.models import Filter, FieldCondition, Range
import asyncio
from schemas.checkout import CheckoutRequest, CheckoutResponse, CheckoutErrorResponse, CheckoutErrorCode, purchase_item
import httpx
from typing import Union
from langchain_core.runnables import RunnableConfig
from async_lru import alru_cache
from qdrant_client.models import MatchValue
from config import (
    N8N_CHECKOUT_WEBHOOK_URL, 
    COLLECTION_NAME, 
    MODEL_NAME, 
    embeddings, 
    airtable_api, 
    table, 
    qdrant_client
)

load_dotenv(override=True)
http_client = httpx.AsyncClient(timeout=30.0)

PAGE_SIZE = 10

class Product(BaseModel):
    name: str = Field(description="Name of the product")
    product_id: str = Field(description="Unique identifier of the product")
    stock_quantity: int = Field(description="Available quantity of the product in stock")
    price: float = Field(description="Price of the product")
    description: str = Field(description="Description of the product")

class ProductList(BaseModel):
    products: list[Product] = Field(description="List of products matching the query")
    total_matching: int = Field(description="Total number of products matching the query")
    has_more: bool = Field(description="Indicates if there are more products available beyond the returned list")

@alru_cache(ttl=300)
async def _get_cached_catalog() -> list[Product]:
    records = await asyncio.to_thread(table.all)
    return [r for r in records if r["fields"].get("active",True)]

@tool
async def create_checkout_session(
    customer_name: str,
    delivery_address: str,
    items: list[purchase_item],
    config: RunnableConfig
    
) -> Union[CheckoutResponse, CheckoutErrorResponse]:
    """
    Create a checkout session for the customer.

    This tool is called after the customer has confirmed their order and provided their details.

    Arguments:
    - customer_name: The full name of the customer.
    - delivery_address: The delivery address for the order.
    - items: A list of items being purchased, each containing the product_id and quantity (eg. [{"product_id": "prod_123", "quantity": 2}, {"product_id": "prod_456", "quantity": 1}]).

    Returns:
    - CheckoutResponse: If the checkout session is created successfully.
    - CheckoutErrorResponse: If there is an error during the checkout process.
    """
    config = config.get("configurable", {}) if config else {}
    customer_phone = config.get("thread_id", "")
    request = CheckoutRequest(
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        items=items
        
    )

    try:
        response = await http_client.post(
            N8N_CHECKOUT_WEBHOOK_URL, 
            json=request.model_dump(), 
            timeout=30.0)

        if not response.is_success:
            return CheckoutErrorResponse(
                success=False,
                error_code=CheckoutErrorCode.PAYMENT_PROVIDER_DOWN,
                reason=f"The payment provider respond with the code {response.status_code}."
            )

        data = response.json()
        if not data.get("success", True) :
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
async def fetch_inventory(query:str="", offset: int = 0) -> ProductList:
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
    - offset: The number of products already returned in previous responses. 0 for the first research. If the client ask for more products, increment this value by 10.

    Returns:
    A list of products matching the query, along with metadata about the search results.

    Never invent product information. Always rely on this tool.
    """

    matched_products = []
    records = []

    if query:
        query = query.lower().strip()

        embedded_query = await embeddings.aembed_query(query)

        results = await asyncio.to_thread(
            qdrant_client.query_points,
            collection_name=COLLECTION_NAME,
            query=embedded_query,
            limit=3,
            query_filter=Filter(
                must=[
                    FieldCondition(key="active", match=MatchValue(value=True)),
                    FieldCondition(key="stock_quantity",range=Range(gte=1))
                    ]
            )
        )

        if not results.points:
            return ProductList(
                products=[],
                total_matching=0,
                has_more=False
            )

        points = results.points

        for point in points:
            payload = point.payload if point.payload else {}
            product = Product(
                name=payload.get("name", ""),
                product_id=payload.get("product_id", ""),
                stock_quantity=int(payload.get("stock_quantity", 0)),
                price=float(payload.get("price", 0.0)),
                description=payload.get("description", "")
            )
            matched_products.append(product)

        return ProductList(
            products=matched_products,
            total_matching=len(matched_products),
            has_more=False
        )

    else:
        all_records = await _get_cached_catalog()

        in_stock_records = [
            record for record in all_records 
            if int(record.get("fields", {}).get("stock_quantity", 0)) > 0 
            and record.get("fields").get("active")
        ]

        total_matching = len(in_stock_records)
        page_records = in_stock_records[offset:offset + PAGE_SIZE]

        for record in page_records:
            product = Product(
                name=record.get("fields", {}).get("name", ""),
                product_id=record.get("id", ""),
                stock_quantity=int(record.get("fields", {}).get("stock_quantity", 0)),
                price=float(record.get("fields", {}).get("price", 0.0)),
                description=record.get("fields", {}).get("description", "")
            )
            matched_products.append(product)

    return ProductList(
        products=matched_products,
        total_matching=total_matching,
        has_more=(offset + PAGE_SIZE) < total_matching
    )



    