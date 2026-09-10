from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


class SubscriptionRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._subs = db.subscriptions
        self._plans = db.plans

    async def seed_default_plans(self) -> None:
        now = datetime.now(timezone.utc)
        plans = [
            {
                "_id": "FREE",
                "name": "Free",
                "max_bots": 5,
                "broadcasts_per_day": -1,
                "price_inr": 0,
                "price_display": "Free",
                "features": [
                    "Up to 5 contact bots",
                    "Unlimited broadcasts",
                    "ReplyDmBot branding on /start",
                ],
            },
            {
                "_id": "PREMIUM",
                "name": "Premium",
                "max_bots": 50,
                "broadcasts_per_day": -1,
                "price_inr": 299,
                "price_display": "₹299/month",
                "features": [
                    "Up to 50 contact bots",
                    "Unlimited broadcasts",
                    "No branding on /start",
                    "Priority support",
                ],
            },
        ]
        for plan in plans:
            plan["updated_at"] = now
            await self._plans.update_one(
                {"_id": plan["_id"]},
                {"$set": plan, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )

    async def get_plan(self, plan_id: str) -> dict | None:
        return await self._plans.find_one({"_id": plan_id})

    async def get_all_plans(self) -> list[dict]:
        cursor = self._plans.find().sort("_id", 1)
        return await cursor.to_list(length=20)

    async def get_active_subscription(self, owner_id: int) -> dict | None:
        now = datetime.now(timezone.utc)
        return await self._subs.find_one(
            {
                "owner_id": owner_id,
                "status": "active",
                "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
            }
        )

    async def get_owner_plan_id(self, owner_id: int) -> str:
        sub = await self.get_active_subscription(owner_id)
        if sub:
            return sub.get("plan_id", "FREE")
        return "FREE"

    async def grant_premium(
        self,
        owner_id: int,
        plan_id: str = "PREMIUM",
        days: int | None = None,
        granted_by: int | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        expires_at = None
        if days:
            from datetime import timedelta
            expires_at = now + timedelta(days=days)

        doc = {
            "owner_id": owner_id,
            "plan_id": plan_id,
            "status": "active",
            "expires_at": expires_at,
            "granted_by": granted_by,
            "payment_method": "manual",
            "updated_at": now,
        }
        result = await self._subs.find_one_and_update(
            {"owner_id": owner_id},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result or doc

    async def revoke_premium(self, owner_id: int) -> None:
        await self._subs.update_one(
            {"owner_id": owner_id},
            {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}},
        )

    async def count_premium_owners(self) -> int:
        now = datetime.now(timezone.utc)
        return await self._subs.count_documents(
            {
                "plan_id": "PREMIUM",
                "status": "active",
                "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
            }
        )

    async def count_by_plan(self, plan_id: str) -> int:
        now = datetime.now(timezone.utc)
        return await self._subs.count_documents(
            {
                "plan_id": plan_id,
                "status": "active",
                "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
            }
        )

    async def get_all_subscriptions(self, skip: int = 0, limit: int = 50) -> list[dict]:
        cursor = self._subs.find({"status": "active"}).sort("updated_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
