from datetime import datetime, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase


class BroadcastRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._jobs = db.broadcast_jobs
        self._recipients = db.broadcast_recipients

    async def create_job(
        self,
        bot_id: int,
        owner_id: int,
        source_chat_id: int,
        source_msg_id: int,
        target: str = "bot_users",
    ) -> str:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        await self._jobs.insert_one(
            {
                "job_id": job_id,
                "bot_id": bot_id,
                "owner_id": owner_id,
                "source_chat_id": source_chat_id,
                "source_msg_id": source_msg_id,
                "target": target,
                "status": "pending",
                "total": 0,
                "sent": 0,
                "failed": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        return job_id

    async def create_system_job(
        self,
        owner_id: int,
        source_chat_id: int,
        source_msg_id: int,
        target: str,
    ) -> str:
        """System-wide broadcast (owners or all end-users). bot_id=0 marks system jobs."""
        return await self.create_job(
            bot_id=0,
            owner_id=owner_id,
            source_chat_id=source_chat_id,
            source_msg_id=source_msg_id,
            target=target,
        )

    async def create_text_job(
        self,
        bot_id: int,
        owner_id: int,
        text: str,
        target: str = "bot_users",
        parse_mode: str = "HTML",
    ) -> str:
        """Text-only broadcast (used by web admin when no Telegram message exists)."""
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        await self._jobs.insert_one(
            {
                "job_id": job_id,
                "bot_id": bot_id,
                "owner_id": owner_id,
                "target": target,
                "payload": {"type": "text", "text": text, "parse_mode": parse_mode},
                "status": "pending",
                "total": 0,
                "sent": 0,
                "failed": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        return job_id

    async def create_compose_job(
        self,
        bot_id: int,
        owner_id: int,
        messages: list[dict],
        audience: str = "all",
        silent: bool = False,
    ) -> str:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        await self._jobs.insert_one(
            {
                "job_id": job_id,
                "bot_id": bot_id,
                "owner_id": owner_id,
                "target": "bot_users",
                "payload": {
                    "type": "multi_copy",
                    "messages": messages,
                    "audience": audience,
                    "silent": silent,
                },
                "status": "pending",
                "total": 0,
                "sent": 0,
                "failed": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        return job_id

    async def count_owner_broadcasts_today(self, owner_id: int) -> int:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return await self._jobs.count_documents(
            {
                "owner_id": owner_id,
                "created_at": {"$gte": start_of_day},
                "status": {"$ne": "cancelled"},
            }
        )

    async def add_recipients(self, job_id: str, user_ids: list[int]) -> None:
        if not user_ids:
            return
        now = datetime.now(timezone.utc)
        docs = [
            {"job_id": job_id, "user_id": uid, "status": "pending", "created_at": now}
            for uid in user_ids
        ]
        try:
            await self._recipients.insert_many(docs, ordered=False)
        except Exception:
            pass

    async def get_running_jobs(self) -> list[dict]:
        cursor = self._jobs.find({"status": {"$in": ["pending", "running"]}})
        return await cursor.to_list(length=50)

    async def get_job(self, job_id: str) -> dict | None:
        return await self._jobs.find_one({"job_id": job_id})

    async def update_job(self, job_id: str, **fields) -> None:
        fields["updated_at"] = datetime.now(timezone.utc)
        await self._jobs.update_one({"job_id": job_id}, {"$set": fields})

    async def cancel_job(self, job_id: str, owner_id: int | None = None) -> bool:
        query: dict = {
            "job_id": job_id,
            "status": {"$in": ["pending", "running"]},
        }
        if owner_id is not None:
            query["owner_id"] = owner_id
        result = await self._jobs.update_one(
            query,
            {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0

    async def get_pending_recipients(self, job_id: str, limit: int = 200) -> list[dict]:
        cursor = self._recipients.find({"job_id": job_id, "status": "pending"}).limit(limit)
        return await cursor.to_list(length=limit)

    async def mark_recipient(self, job_id: str, user_id: int, status: str) -> None:
        await self._recipients.update_one(
            {"job_id": job_id, "user_id": user_id},
            {"$set": {"status": status}},
        )

    async def count_recipients(self, job_id: str) -> int:
        return await self._recipients.count_documents({"job_id": job_id})
