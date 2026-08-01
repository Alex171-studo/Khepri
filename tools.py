from langchain.tools import tool
from dotenv import load_dotenv
import os
from pyairtable import Api
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
import asyncio

load_dotenv(override=True)

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
orders_table = airtable.table(AIRTABLE_BASE_ID, "Orders")

class Product(BaseModel):
    name: str = Field(description="Name of the product")
    product_id: str = Field(description="Unique identifier of the product")
    stock_quantity: int = Field(description="Available quantity of the product in stock")
    price: float = Field(description="Price of the product")
    description: str = Field(description="Description of the product")


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
            product_id=fields.get('product_id', ''),
            stock_quantity=int(fields.get('stock_quantity', 0)),
            price=float(fields.get('price', 0.0)),
            description=fields.get('description', '')
        )
        matched_products.append(product)

    return matched_products

@tool
async def record_order(customer_name: str, customer_phone: str, product_id: str, quantity: int) -> str:
    """
        Create a customer order.

        Call this tool ONLY after the customer has confirmed the purchase.

        Requirements before calling:
        - A valid product has been identified.
        - The requested quantity is known.
        - The requested quantity is available.
        - The customer's full name is known.
        - The customer's phone number is known.

        Never call this tool if any required information is missing.
        Never invent or guess any argument.

        Behavior:
        - Verifies that the product exists.
        - Verifies that enough stock is available.
        - Decreases the stock.
        - Creates the order with status "pending".
        - Returns either a success message or an error message.

        Do not retry automatically if this tool returns an error.

    """
    
    new_order = {
        "customer_phone": customer_phone,
        "product_id": product_id,
        "quantity": quantity,
        "customer_name": customer_name,
        "status": "pending",
    }

    product = await asyncio.to_thread(stocks_table.first, formula=f"{{product_id}}='{product_id}'")
    if not product:
        return f"Product with ID {product_id} not found in inventory."

    else:
        available_quantity = int(product['fields'].get('stock_quantity', 0))

        if quantity > available_quantity:
            return f"Insufficient stock for product {product_id}. Available: {available_quantity}, Requested: {quantity}."

        new_quantity = available_quantity - quantity
        await asyncio.to_thread(stocks_table.update, product['id'], {"stock_quantity": new_quantity})

    record = await asyncio.to_thread(orders_table.create, new_order)
    record_id = record["fields"]["order_id"]
    return f"Order {record_id} recorded successfully for {customer_name} (Status: pending)."