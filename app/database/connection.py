import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

_MONGO_DISK_ERROR = 14031


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
        try:
            await self._create_indexes(db)
        except OperationFailure as e:
            if e.code == _MONGO_DISK_ERROR:
                logger.critical(
                    "MongoDB out of disk space (code %s). Railway's 500 MB Mongo volume "
                    "cannot satisfy Mongo's 512 MB free-space requirement. Fix: (1) Hobby plan "
                    "→ MongoDB volume → Live Resize to 1024 MB+, or (2) use MongoDB Atlas M0 "
                    "and set MONGODB_URI on contactbot (see DEPLOY_ATLAS.md). Continuing "
                    "without indexes — use Atlas or resize volume for production.",
                    _MONGO_DISK_ERROR,
                )
                return
            raise

    async def _create_indexes(self, db: AsyncIOMotorDatabase) -> None:
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
