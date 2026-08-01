import os
from dotenv import load_dotenv
from pyairtable import Api
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

load_dotenv(override=True)

COLLECTION_NAME = "khepri_products"
MODEL_NAME = "text-embedding-3-small"

airtable_api = Api(os.environ.get("AIRTABLE_API_KEY"))
table = airtable_api.table(os.environ.get("AIRTABLE_BASE_ID"), os.environ.get("AIRTABLE_TABLE_NAME"))

embeddings = OpenAIEmbeddings(model=MODEL_NAME)

qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
)

def reindex_catalog():

    print("🔄 [1/4] Fetching all products from Airtable...")
    records = table.all()
    print(f"✅ Fetched {len(records)} products from Airtable.")

    if not records:
        print("No records found in Airtable.")
        return

    print("🔄 [2/4] Recreating Qdrant collection...")

    if qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        qdrant_client.delete_collection(collection_name=COLLECTION_NAME)

    qdrant_client.create_collection(
         collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

    points = []

    print("🔄 [3/4] Generating embeddings and preparing points for Qdrant...")

    texts_to_embed = []
    payloads = []
    point_ids = []

    for record in records:
        product_data = record['fields']
        product_id = record['id']
     
        product_name = product_data.get('name', '')
        product_description = product_data.get('description', '')
        product_price = float(product_data.get('price', 0.0))

        text_to_embed = f"Product: {product_name}\n Description: {product_description}\n Price: ${product_price:.2f}"
        qdrant_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, product_id))
        texts_to_embed.append(text_to_embed)
        point_ids.append(qdrant_uuid)
        payloads.append({
            "airtable_id": product_id,
            "name": product_name,
            "description": product_description,
            "text": text_to_embed
        })

    embedding_vectors = embeddings.embed_documents(texts_to_embed)
    points = [
        PointStruct(id=pid, vector=vec, payload=payload) 
        for pid, vec, payload in zip(point_ids, embedding_vectors, payloads)
    ]

    print(f"🔄 [4/4] Upserting {len(points)} points into Qdrant...")
    qdrant_client.upsert(collection_name=COLLECTION_NAME,points=points)
    print("✅ Indexing complete. All products have been indexed into Qdrant.")


if __name__ == "__main__":
    reindex_catalog()