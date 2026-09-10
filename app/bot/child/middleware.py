from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database.repositories import (
    AppSettingsRepository,
    BotRepository,
    BotUserRepository,
    BroadcastRepository,
)
from app.services.entitlement_service import EntitlementService
from app.services.relay_service import RelayService


class ChildBotMiddleware(BaseMiddleware):
    def __init__(
        self,
        bot_doc: dict,
        relay: RelayService,
        bot_repo: BotRepository,
        user_repo: BotUserRepository,
        broadcast_repo: BroadcastRepository,
        entitlement: EntitlementService,
        app_settings: AppSettingsRepository,
    ) -> None:
        self.bot_doc = bot_doc
        self.relay = relay
        self.bot_repo = bot_repo
        self.user_repo = user_repo
        self.broadcast_repo = broadcast_repo
        self.entitlement = entitlement
        self.app_settings = app_settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["bot_doc"] = self.bot_doc
        data["relay"] = self.relay
        data["bot_repo"] = self.bot_repo
        data["user_repo"] = self.user_repo
        data["broadcast_repo"] = self.broadcast_repo
        data["entitlement"] = self.entitlement
        data["app_settings"] = self.app_settings
        return await handler(event, data)
