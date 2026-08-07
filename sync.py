import json
import asyncio
from datetime import datetime, timezone, timedelta
from qdrant_service import upsert_products
from tools import _get_cached_catalog
from config import table, airtable_api, SYNC_INTERVAL, STATE_FILE
import os

def load_last_timestamp():
    """Load the last synchronization timestamp"""

    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data.get("last_timestamp")

def save_timestamp(timestamp:str):
    """Save synchronization timestamp"""

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump({"last_timestamp":timestamp}, file, indent=4)

def parse_iso(ts_str:str) -> datetime:
    """Convert a ISO chain in datetime with timezone UTC"""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

def get_record_timestamp(record):
    """Extract Airtable last_modified timestamp"""
    return record.get("fields").get("last_modified_time")

def get_latest_timestamp(records):
    """Return the most modification timestamp"""
    
    raw_timestamps = [get_record_timestamp(record) for record in records]
    timestamps = [ts for ts in raw_timestamps if ts is not None]

    if not timestamps:
        return None

    dt_objects = [parse_iso(ts) for ts in timestamps]
    latest_dt = max(dt_objects)
    return latest_dt.isoformat()

async def sync_products():
    last_timestamp = load_last_timestamp()

    if last_timestamp is None:
        print("🟡 First synchronization. Initializing timestamp...")
        records = await asyncio.to_thread(table.all)
        latest = get_latest_timestamp(records)
        if latest:
            save_timestamp(latest)
        return

    dt_last = parse_iso(last_timestamp)
    safe_timestamp = dt_last - timedelta(seconds=2)

    formatted_time = safe_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    formula = f"IS_AFTER({{last_modified_time}}, '{formatted_time}')"
    records = await asyncio.to_thread(table.all, formula=formula)

    if not records:
        return

    print(f"🔄 {len(records)} products changed.")
    for record in records:
        print(record.get("fields").get("name"))
    await asyncio.to_thread(upsert_products, records)
    _get_cached_catalog.cache_clear()

    latest = get_latest_timestamp(records)
    if latest:
        if parse_iso(latest) > dt_last:
            save_timestamp(latest)

    print("✅ Synchronization complete.")

async def start_sync_loop():

    print("🚀 Airtable synchronization started.")
    
    while True:
        try:
            await sync_products()
        except Exception as error:
            print("❌ Sync error:",error)

        await asyncio.sleep(SYNC_INTERVAL)



