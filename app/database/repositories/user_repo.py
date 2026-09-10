from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


class BotUserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.bot_users

    async def upsert(
        self,
        bot_id: int,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str | None = None,
    ) -> tuple[dict, bool]:
        """Returns (user_doc, is_new)."""
        now = datetime.now(timezone.utc)
        existing = await self._col.find_one({"bot_id": bot_id, "user_id": user_id})
        is_new = existing is None

        await self._col.update_one(
            {"bot_id": bot_id, "user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                    "language_code": language_code,
                    "last_active": now,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "bot_id": bot_id,
                    "user_id": user_id,
                    "created_at": now,
                    "blocked": False,
                },
            },
            upsert=True,
        )
        doc = await self._col.find_one({"bot_id": bot_id, "user_id": user_id})
        return doc or {}, is_new

    async def get_all_active(self, bot_id: int) -> list[dict]:
        cursor = self._col.find({"bot_id": bot_id, "blocked": False})
        return await cursor.to_list(length=1_000_000)

    async def count(self, bot_id: int) -> int:
        return await self._col.count_documents({"bot_id": bot_id})

    async def mark_blocked(self, bot_id: int, user_id: int) -> None:
        await self._col.update_one(
            {"bot_id": bot_id, "user_id": user_id},
            {"$set": {"blocked": True}},
        )

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    async def get_distinct_owner_user_ids(self) -> list[int]:
        """All telegram IDs registered as bot end-users across the system."""
        return await self._col.distinct("user_id")

    async def get_broadcast_recipient_ids(self, bot_id: int, audience: str) -> list[int]:
        query: dict = {"bot_id": bot_id, "blocked": False}
        if audience == "active":
            since = datetime.now(timezone.utc) - timedelta(days=30)
            query["last_active"] = {"$gte": since}
        cursor = self._col.find(query)
        users = await cursor.to_list(length=1_000_000)
        if audience == "username":
            return [u["user_id"] for u in users if u.get("username")]
        return [u["user_id"] for u in users]

    async def count_broadcast_audience(self, bot_id: int, audience: str) -> int:
        return len(await self.get_broadcast_recipient_ids(bot_id, audience))

    async def should_send_auto_reply(
        self, bot_id: int, user_id: int, cooldown_seconds: int
    ) -> bool:
        if cooldown_seconds <= 0:
            return True
        doc = await self._col.find_one({"bot_id": bot_id, "user_id": user_id})
        if not doc:
            return True
        last = doc.get("last_auto_reply_at")
        if not last:
            return True
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= last + timedelta(seconds=cooldown_seconds)

    async def mark_auto_reply_sent(self, bot_id: int, user_id: int) -> None:
        await self._col.update_one(
            {"bot_id": bot_id, "user_id": user_id},
            {"$set": {"last_auto_reply_at": datetime.now(timezone.utc)}},
        )
