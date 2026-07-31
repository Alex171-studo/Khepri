import os
from dotenv import load_dotenv
from pyairtable import Api
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv(override=True)

COLLECTION_NAME = "khepri_products"
MODEL_NAME = "text-embedding-3-small"

airtable_api = Api(os.environ.get("AIRTABLE_API_KEY"))
table = airtable_api.table(os.environ.get("AIRTABLE_BASE_ID"), os.environ.get("AIRTABLE_TABLE_NAME"))

embeddings = OpenAIEmbeddings(
    model=MODEL_NAME, 
    openai_api_key=os.environ.get("OPENAI_API_KEY")
)

qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
    cloud_inference=True
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

    for idx, record in enumerate(records):
        product_data = record['fields']
        product_id = record['id']
     
        product_name = product_data.get('name', '')
        product_description = product_data.get('description', '')
        product_price = product_data.get('price', 0.0)

        text_to_embed = f"Product: {product_name}\n Description: {product_description}\n Price: ${product_price:.2f}"

        embedding_vector = embeddings.embed_query(text_to_embed)

        point = PointStruct(
            id=idx+1,
            vector=embedding_vector,
            payload={
                "airtable_id": product_id,
                "name": product_name,
                "description": product_description,
                "text": text_to_embed
            }
        )
        points.append(point)

    print(f"🔄 [4/4] Upserting {len(points)} points into Qdrant...")
    qdrant_client.upsert(collection_name=COLLECTION_NAME,points=points)
    print("✅ Indexing complete. All products have been indexed into Qdrant.")


if __name__ == "__main__":
    reindex_catalog()