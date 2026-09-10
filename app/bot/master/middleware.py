from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.config import Settings
from app.database.repositories import (
    BotRepository,
    OwnerRepository,
    BotUserRepository,
    BroadcastRepository,
    SubscriptionRepository,
)
from app.services.bot_manager import BotManager
from app.services.entitlement_service import EntitlementService


class MasterMiddleware(BaseMiddleware):
    def __init__(
        self,
        settings: Settings,
        bot_repo: BotRepository,
        owner_repo: OwnerRepository,
        user_repo: BotUserRepository,
        broadcast_repo: BroadcastRepository,
        subscription_repo: SubscriptionRepository,
        entitlement: EntitlementService,
        bot_manager: BotManager,
    ) -> None:
        self.settings = settings
        self.bot_repo = bot_repo
        self.owner_repo = owner_repo
        self.user_repo = user_repo
        self.broadcast_repo = broadcast_repo
        self.subscription_repo = subscription_repo
        self.entitlement = entitlement
        self.bot_manager = bot_manager

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        is_super_admin = bool(
            user and user.id in self.settings.super_admin_id_list
        )
        data["settings"] = self.settings
        data["bot_repo"] = self.bot_repo
        data["owner_repo"] = self.owner_repo
        data["user_repo"] = self.user_repo
        data["broadcast_repo"] = self.broadcast_repo
        data["subscription_repo"] = self.subscription_repo
        data["entitlement"] = self.entitlement
        data["bot_manager"] = self.bot_manager
        data["is_super_admin"] = is_super_admin
        return await handler(event, data)
