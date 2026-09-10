from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


class MessageMapRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.message_map

    async def create(
        self,
        bot_id: int,
        user_id: int,
        user_msg_id: int,
        admin_chat_id: int,
        admin_msg_id: int,
        direction: str,
    ) -> None:
        await self._col.insert_one(
            {
                "bot_id": bot_id,
                "user_id": user_id,
                "user_msg_id": user_msg_id,
                "admin_chat_id": admin_chat_id,
                "admin_msg_id": admin_msg_id,
                "direction": direction,
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def find_by_admin_msg(
        self, bot_id: int, admin_chat_id: int, admin_msg_id: int
    ) -> dict | None:
        return await self._col.find_one(
            {"bot_id": bot_id, "admin_chat_id": admin_chat_id, "admin_msg_id": admin_msg_id}
        )

    async def find_by_user_msg(
        self, bot_id: int, user_id: int, user_msg_id: int
    ) -> dict | None:
        return await self._col.find_one(
            {"bot_id": bot_id, "user_id": user_id, "user_msg_id": user_msg_id}
        )
