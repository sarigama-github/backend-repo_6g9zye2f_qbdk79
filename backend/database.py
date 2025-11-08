import os
from typing import Any, Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "vibe_app")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(DATABASE_URL)
        _db = _client[DATABASE_NAME]
    return _db

async def create_document(collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_db()
    now = datetime.utcnow()
    data = {**data, "created_at": now, "updated_at": now}
    result = await db[collection].insert_one(data)
    created = await db[collection].find_one({"_id": result.inserted_id})
    if created and "_id" in created:
        created["_id"] = str(created["_id"])
    return created or {}

async def get_documents(collection: str, filter_dict: Dict[str, Any] | None = None, limit: int = 100) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = db[collection].find(filter_dict or {}).limit(limit).sort("created_at", -1)
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items

async def update_document(collection: str, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from bson import ObjectId
    db = await get_db()
    updates["updated_at"] = datetime.utcnow()
    result = await db[collection].find_one_and_update(
        {"_id": ObjectId(doc_id)}, {"$set": updates}, return_document=True
    )
    if result and "_id" in result:
        result["_id"] = str(result["_id"])
    return result

async def delete_document(collection: str, doc_id: str) -> bool:
    from bson import ObjectId
    db = await get_db()
    res = await db[collection].delete_one({"_id": ObjectId(doc_id)})
    return res.deleted_count == 1
