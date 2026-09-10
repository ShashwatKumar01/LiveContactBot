from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class DatabaseManager:
    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self, uri: str, database: str) -> None:
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[database]
        await self._client.admin.command("ping")

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()

    async def create_indexes(self) -> None:
        db = self.db

        await db.bots.create_index("bot_id", unique=True)
        await db.bots.create_index("owner_id")
        await db.bots.create_index([("owner_id", 1), ("username", 1)])

        await db.bot_users.create_index(
            [("bot_id", 1), ("user_id", 1)], unique=True
        )
        await db.bot_users.create_index("bot_id")

        await db.message_map.create_index(
            [("bot_id", 1), ("admin_chat_id", 1), ("admin_msg_id", 1)]
        )
        await db.message_map.create_index(
            [("bot_id", 1), ("user_id", 1), ("user_msg_id", 1)]
        )

        await db.broadcast_jobs.create_index([("bot_id", 1), ("status", 1)])
        await db.broadcast_jobs.create_index([("owner_id", 1), ("created_at", -1)])

        await db.subscriptions.create_index("owner_id", unique=True)
        await db.subscriptions.create_index([("plan_id", 1), ("status", 1)])
        await db.plans.create_index("_id", unique=True)
        await db.broadcast_recipients.create_index(
            [("job_id", 1), ("status", 1)]
        )
        await db.broadcast_recipients.create_index(
            [("job_id", 1), ("user_id", 1)], unique=True
        )

        await db.owners.create_index("telegram_id", unique=True)

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db


db_manager = DatabaseManager()
