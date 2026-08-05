import uuid

from qdrant_client.models import(
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
    PointIdsList
)
from config import qdrant_client, COLLECTION_NAME, embeddings, batch_size


# -----------------------------------------------------------------------------------------------------------------
# COLLECTION MANAGEMENT
# -----------------------------------------------------------------------------------------------------------------

def recreate_collection():
    """
    Recreates the Qdrant collection for products.
    Deletes the existing collection if it exists and creates a new one with the specified configuration.
    Using during a full reindexing of the catalog to ensure a clean state.
    """
    if qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        qdrant_client.delete_collection(collection_name=COLLECTION_NAME)

    qdrant_client.create_collection(
         collection_name=COLLECTION_NAME,
         vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

    qdrant_client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="stock_quantity",
        field_schema=PayloadSchemaType.INTEGER,
    )

    qdrant_client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="price",
        field_schema=PayloadSchemaType.FLOAT,
    )

    qdrant_client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="active",
        field_schema=PayloadSchemaType.BOOL
    )

# -----------------------------------------------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------------------------------------------

def build_text_to_embedded(fields: dict) -> str:
    """
    Constructs a text representation of the product from its fields.
    This text is used for generating embeddings for semantic search.
    """
    name = fields.get("name", "")
    description = fields.get("description", "")
    return f"Product: {name}\n Description: {description}\n".strip()

def build_payload(record: dict) -> dict:
    """
    Constructs the payload dictionary for a product to be stored in Qdrant.
    This includes essential product information such as ID, name, description, price, and stock quantity.
    """
    product_id = record.get("id", "")
    fields = record.get("fields", record)
    return {
        "product_id": product_id,
        "active": fields.get("active", False),
        "name": fields.get("name", ""),
        "description": fields.get("description", ""),
        "price": fields.get("price", 0.0),
        "stock_quantity": fields.get("stock_quantity", 0),
        "text": build_text_to_embedded(fields)
    }

def build_id(product_id:str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, product_id))

# -----------------------------------------------------------------------------------------------------------------
# UPSERTS
# -----------------------------------------------------------------------------------------------------------------

def upsert_product(record:dict): 
    """
    Upsert a single Airtable record
    """

    payload = build_payload(record)

    vector = embeddings.embed_query(payload["text"])

    point = PointStruct(
        id=build_id(payload["product_id"]),
        vector=vector,
        payload=payload
    )

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point]
    )

def upsert_products(records:list[dict]):
    """"
    Upserts multiple Airtable records in one request.
    This is most faster than calling embedded_query once per product
    """

    if not records:
        return 

    payloads = [ build_payload(record) for record in records]
    texts = [payload["text"] for payload in payloads]

    vectors = embeddings.embed_documents(texts)
    points = []

    for payload, vector in zip(payloads, vectors):
        point = PointStruct(
            id = build_id(payload["product_id"]),
            vector=vector,
            payload=payload
        )

        points.append(point)

    for i in range(0, len(points), batch_size):
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i: i+batch_size]
        )

# -----------------------------------------------------------------------------------------------------------------
# DELETE
# -----------------------------------------------------------------------------------------------------------------

def delete_product(product_id:str):
    """
    Delete one product from Qdrant
    """

    point_id = build_id(product_id)
    qdrant_client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=PointIdsList(points=[point_id])
    )
