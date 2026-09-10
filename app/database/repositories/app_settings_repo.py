from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants import DEFAULT_CHILD_PROMO_FOOTER

PROMO_FOOTER_KEY = "child_start_promo_footer"


class AppSettingsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.app_settings

    async def ensure_defaults(self) -> None:
        now = datetime.now(timezone.utc)
        await self._col.update_one(
            {"_id": PROMO_FOOTER_KEY},
            {
                "$setOnInsert": {
                    "value": DEFAULT_CHILD_PROMO_FOOTER,
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )

    async def get_child_start_promo_footer(self) -> str:
        doc = await self._col.find_one({"_id": PROMO_FOOTER_KEY})
        if doc and doc.get("value"):
            return str(doc["value"])
        return DEFAULT_CHILD_PROMO_FOOTER

    async def set_child_start_promo_footer(self, value: str) -> None:
        now = datetime.now(timezone.utc)
        await self._col.update_one(
            {"_id": PROMO_FOOTER_KEY},
            {"$set": {"value": value, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
