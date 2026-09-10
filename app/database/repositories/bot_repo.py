from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.constants import DEFAULT_LOCALES


class BotRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.bots

    async def create(
        self,
        bot_id: int,
        owner_id: int,
        token_encrypted: str,
        username: str,
        first_name: str,
    ) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "bot_id": bot_id,
            "owner_id": owner_id,
            "token_encrypted": token_encrypted,
            "username": username,
            "first_name": first_name,
            "status": "active",
            "group_id": None,
            "anonymous": False,
            "locales": DEFAULT_LOCALES.copy(),
            "default_locale": "en",
            "stats": {
                "incoming_messages": 0,
                "outgoing_messages": 0,
                "total_users": 0,
                "active_users_30d": 0,
            },
            "created_at": now,
            "updated_at": now,
        }
        await self._col.insert_one(doc)
        return doc

    async def get_by_id(self, bot_id: int) -> dict | None:
        return await self._col.find_one({"bot_id": bot_id})

    async def get_by_owner(self, owner_id: int) -> list[dict]:
        cursor = self._col.find({"owner_id": owner_id}).sort("created_at", -1)
        return await cursor.to_list(length=100)

    async def get_all_active(self) -> list[dict]:
        cursor = self._col.find({"status": "active"})
        return await cursor.to_list(length=10_000)

    async def update(self, bot_id: int, **fields) -> None:
        fields["updated_at"] = datetime.now(timezone.utc)
        await self._col.update_one({"bot_id": bot_id}, {"$set": fields})

    async def increment_stat(self, bot_id: int, field: str, amount: int = 1) -> None:
        await self._col.update_one(
            {"bot_id": bot_id},
            {"$inc": {f"stats.{field}": amount}},
        )

    async def disconnect(self, bot_id: int, owner_id: int) -> bool:
        result = await self._col.update_one(
            {"bot_id": bot_id, "owner_id": owner_id},
            {"$set": {"status": "disconnected", "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0

    async def count_by_owner(self, owner_id: int) -> int:
        return await self._col.count_documents({"owner_id": owner_id, "status": "active"})

    async def token_exists(self, bot_id: int) -> bool:
        doc = await self._col.find_one({"bot_id": bot_id}, {"_id": 1})
        return doc is not None

    async def reactivate(
        self,
        bot_id: int,
        owner_id: int,
        token_encrypted: str,
        username: str,
        first_name: str,
    ) -> dict | None:
        now = datetime.now(timezone.utc)
        return await self._col.find_one_and_update(
            {"bot_id": bot_id, "owner_id": owner_id},
            {
                "$set": {
                    "status": "active",
                    "token_encrypted": token_encrypted,
                    "username": username,
                    "first_name": first_name,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def count_all(self, status: str | None = None) -> int:
        query = {"status": status} if status else {}
        return await self._col.count_documents(query)

    async def get_all(self, skip: int = 0, limit: int = 20) -> list[dict]:
        cursor = self._col.find().sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def admin_disable(self, bot_id: int, reason: str = "") -> bool:
        result = await self._col.update_one(
            {"bot_id": bot_id},
            {
                "$set": {
                    "status": "disabled",
                    "disabled_reason": reason,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def admin_enable(self, bot_id: int) -> bool:
        result = await self._col.update_one(
            {"bot_id": bot_id},
            {"$set": {"status": "active", "disabled_reason": None, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0

    async def get_global_stats(self) -> dict:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "incoming": {"$sum": "$stats.incoming_messages"},
                    "outgoing": {"$sum": "$stats.outgoing_messages"},
                    "users": {"$sum": "$stats.total_users"},
                }
            }
        ]
        cursor = self._col.aggregate(pipeline)
        rows = await cursor.to_list(length=1)
        if not rows:
            return {"incoming": 0, "outgoing": 0, "users": 0}
        row = rows[0]
        return {
            "incoming": row.get("incoming", 0),
            "outgoing": row.get("outgoing", 0),
            "users": row.get("users", 0),
        }
