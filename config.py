#---------------------------------------------------------------------------------------------------
# Airtable config 
#---------------------------------------------------------------------------------------------------

from pyairtable import Api
import os
from dotenv import load_dotenv

load_dotenv(override=True)
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME", "Stocks") 

airtable_api = Api(AIRTABLE_API_KEY)
table = airtable_api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

#---------------------------------------------------------------------------------------------------
# Qdrant config
#---------------------------------------------------------------------------------------------------

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

batch_size = 100

COLLECTION_NAME = "khepri_products"
MODEL_NAME = "text-embedding-3-small"

embeddings = OpenAIEmbeddings(model=MODEL_NAME, chunk_size=500)

qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
)

#---------------------------------------------------------------------------------------------------
# Sync
#---------------------------------------------------------------------------------------------------
SYNC_INTERVAL = 5

STATE_FILE = "sync_state.json"


N8N_CHECKOUT_WEBHOOK_URL = os.getenv("N8N_CHECKOUT_WEBHOOK_URL")
