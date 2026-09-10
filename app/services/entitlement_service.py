from datetime import datetime, timezone

from app.core.config import Settings
from app.database.repositories import BotRepository, BroadcastRepository, OwnerRepository, SubscriptionRepository


class EntitlementService:
    def __init__(
        self,
        settings: Settings,
        subscription_repo: SubscriptionRepository,
        bot_repo: BotRepository,
        broadcast_repo: BroadcastRepository,
        owner_repo: OwnerRepository,
    ) -> None:
        self._settings = settings
        self._subscription_repo = subscription_repo
        self._bot_repo = bot_repo
        self._broadcast_repo = broadcast_repo
        self._owner_repo = owner_repo

    async def get_plan_limits(self, owner_id: int) -> dict:
        plan_id = await self._subscription_repo.get_owner_plan_id(owner_id)
        plan = await self._subscription_repo.get_plan(plan_id)
        if not plan:
            plan = await self._subscription_repo.get_plan("FREE") or {}

        max_bots = plan.get("max_bots", self._settings.max_bots_free)
        custom_max = await self._owner_repo.get_max_bots(owner_id, max_bots)
        if custom_max != self._settings.max_bots_free:
            max_bots = custom_max

        return {
            "plan_id": plan_id,
            "plan_name": plan.get("name", plan_id),
            "max_bots": max_bots,
            "broadcasts_per_day": plan.get("broadcasts_per_day", -1),
            "is_premium": plan_id == "PREMIUM",
        }

    async def can_add_bot(self, owner_id: int) -> tuple[bool, str]:
        limits = await self.get_plan_limits(owner_id)
        current = await self._bot_repo.count_by_owner(owner_id)
        if current >= limits["max_bots"]:
            if limits["is_premium"]:
                return False, f"You've reached your limit of {limits['max_bots']} bots."
            return (
                False,
                f"Free plan allows {limits['max_bots']} bots. Upgrade to Premium with /pro for up to 50 bots.",
            )
        return True, "OK"

    async def can_broadcast(self, owner_id: int) -> tuple[bool, str]:
        limits = await self.get_plan_limits(owner_id)
        daily_limit = limits["broadcasts_per_day"]
        if daily_limit < 0:
            return True, "OK"

        used = await self._broadcast_repo.count_owner_broadcasts_today(owner_id)
        if used >= daily_limit:
            if limits["is_premium"]:
                return False, f"Daily broadcast limit reached ({daily_limit}/day)."
            return (
                False,
                f"Free plan allows {daily_limit} broadcasts per day. "
                "Upgrade to Premium with /pro for unlimited broadcasts.",
            )
        remaining = daily_limit - used
        return True, f"OK ({remaining} remaining today)"

    async def shows_child_promo_branding(self, owner_id: int) -> bool:
        limits = await self.get_plan_limits(owner_id)
        return not limits.get("is_premium", False)

    async def get_plan_summary(self, owner_id: int) -> dict:
        limits = await self.get_plan_limits(owner_id)
        bot_count = await self._bot_repo.count_by_owner(owner_id)
        used_broadcasts = await self._broadcast_repo.count_owner_broadcasts_today(owner_id)
        daily_limit = limits["broadcasts_per_day"]
        sub = await self._subscription_repo.get_active_subscription(owner_id)

        return {
            **limits,
            "bots_used": bot_count,
            "broadcasts_used_today": used_broadcasts,
            "broadcasts_remaining": (
                "Unlimited" if daily_limit < 0 else max(0, daily_limit - used_broadcasts)
            ),
            "expires_at": sub.get("expires_at") if sub else None,
        }
