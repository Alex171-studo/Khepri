from dotenv import load_dotenv
from config import table
from qdrant_service import recreate_collection, upsert_products

def reindex_catalog():
    """
    Rebuild the entire Qdrant collection from Airtable
    """
    print("🔄 [1/3] Fetching all products from Airtable...")
    records = table.all()
    print(f"✅ Fetched {len(records)} products from Airtable.")

    if not records:
        print("No records found in Airtable.")
        return

    print("🔄 [2/3] Recreating Qdrant collection...")
    recreate_collection()

    print("🔄 [3/3] Indexing products...")
    upsert_products(records)

    print("✅ Catalog sucesfully rebuilt.")


if __name__ == "__main__":
    reindex_catalog()