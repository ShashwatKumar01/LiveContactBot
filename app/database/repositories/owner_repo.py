from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


class OwnerRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.owners

    async def upsert(self, telegram_id: int, **fields) -> dict:
        now = datetime.now(timezone.utc)
        update = {"updated_at": now, **fields}
        await self._col.update_one(
            {"telegram_id": telegram_id},
            {"$set": update, "$setOnInsert": {"telegram_id": telegram_id, "created_at": now}},
            upsert=True,
        )
        return await self.get(telegram_id) or {}

    async def get(self, telegram_id: int) -> dict | None:
        return await self._col.find_one({"telegram_id": telegram_id})

    async def count(self) -> int:
        return await self._col.count_documents({})

    async def get_all(self, skip: int = 0, limit: int = 50) -> list[dict]:
        cursor = self._col.find().sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def ban(self, telegram_id: int, reason: str = "") -> bool:
        result = await self._col.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "banned": True,
                    "ban_reason": reason,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def unban(self, telegram_id: int) -> bool:
        result = await self._col.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "banned": False,
                    "ban_reason": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def is_banned(self, telegram_id: int) -> bool:
        doc = await self.get(telegram_id)
        return bool(doc and doc.get("banned"))

    async def set_max_bots(self, telegram_id: int, max_bots: int) -> None:
        await self.upsert(telegram_id, max_bots=max_bots)

    async def get_max_bots(self, telegram_id: int, default: int) -> int:
        doc = await self.get(telegram_id)
        if doc and doc.get("max_bots") is not None:
            return int(doc["max_bots"])
        return default
