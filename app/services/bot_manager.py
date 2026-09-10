import asyncio
import logging
from dataclasses import dataclass, field

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.crypto import decrypt_token
from app.database.repositories import (
    BotRepository,
    BotUserRepository,
    BroadcastRepository,
    MessageMapRepository,
    OwnerRepository,
)
from app.services.entitlement_service import EntitlementService
from app.services.relay_service import RelayService
from app.bot.child.handlers import create_child_router
from app.bot.child.middleware import ChildBotMiddleware

logger = logging.getLogger(__name__)


@dataclass
class ChildBotInstance:
    bot_id: int
    bot: Bot
    dispatcher: Dispatcher
    task: asyncio.Task | None = None
    username: str = ""


class BotManager:
    """Manages lifecycle of all registered child (contact) bots."""

    def __init__(
        self,
        settings: Settings,
        redis: Redis,
        bot_repo: BotRepository,
        owner_repo: OwnerRepository,
        user_repo: BotUserRepository,
        msg_map_repo: MessageMapRepository,
        broadcast_repo: BroadcastRepository,
        entitlement: EntitlementService | None = None,
    ) -> None:
        self._settings = settings
        self._redis = redis
        self._bot_repo = bot_repo
        self._owner_repo = owner_repo
        self._user_repo = user_repo
        self._msg_map_repo = msg_map_repo
        self._broadcast_repo = broadcast_repo
        self._entitlement = entitlement
        self._instances: dict[int, ChildBotInstance] = {}
        self._web_app: web.Application | None = None
        self._relay = RelayService(bot_repo, user_repo, msg_map_repo)

    def attach_web_app(self, app: web.Application) -> None:
        self._web_app = app

    def set_entitlement(self, entitlement: EntitlementService) -> None:
        self._entitlement = entitlement

    @property
    def relay(self) -> RelayService:
        return self._relay

    @property
    def instances(self) -> dict[int, ChildBotInstance]:
        return self._instances

    def get_bot(self, bot_id: int) -> Bot | None:
        inst = self._instances.get(bot_id)
        return inst.bot if inst else None

    async def start_all(self) -> None:
        bots = await self._bot_repo.get_all_active()
        logger.info("Starting %d active child bots", len(bots))
        for bot_doc in bots:
            try:
                await self.start_bot(bot_doc)
            except Exception as e:
                logger.error("Failed to start bot %s: %s", bot_doc.get("username"), e)

    async def start_bot(self, bot_doc: dict) -> ChildBotInstance:
        bot_id = bot_doc["bot_id"]
        if bot_id in self._instances:
            await self.stop_bot(bot_id)

        token = decrypt_token(bot_doc["token_encrypted"], self._settings.token_encryption_key)
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
        me = await bot.get_me()

        storage = RedisStorage(
            redis=self._redis,
            key_builder=DefaultKeyBuilder(prefix=f"child:{bot_id}"),
        )
        dp = Dispatcher(storage=storage)

        middleware = ChildBotMiddleware(
            bot_doc=bot_doc,
            relay=self._relay,
            bot_repo=self._bot_repo,
            user_repo=self._user_repo,
            broadcast_repo=self._broadcast_repo,
            entitlement=self._entitlement,
        )
        dp.message.middleware(middleware)
        dp.callback_query.middleware(middleware)

        router = create_child_router()
        dp.include_router(router)

        instance = ChildBotInstance(
            bot_id=bot_id,
            bot=bot,
            dispatcher=dp,
            username=me.username or bot_doc.get("username", ""),
        )

        if self._settings.is_production:
            webhook_path = f"/webhook/child/{bot_id}"
            await bot.set_webhook(
                url=f"{self._settings.webhook_host}{webhook_path}",
                secret_token=self._settings.webhook_secret,
            )
            if self._web_app:
                from app.web.app_factory import register_child_webhook

                register_child_webhook(self._web_app, self._settings, instance)
        else:
            instance.task = asyncio.create_task(
                self._poll(instance),
                name=f"child-bot-{bot_id}",
            )

        self._instances[bot_id] = instance
        logger.info("Started child bot @%s (id=%s)", instance.username, bot_id)
        return instance

    async def _poll(self, instance: ChildBotInstance) -> None:
        try:
            await instance.dispatcher.start_polling(
                instance.bot,
                handle_signals=False,
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Polling crashed for bot %s: %s", instance.bot_id, e)

    async def stop_bot(self, bot_id: int) -> None:
        instance = self._instances.pop(bot_id, None)
        if not instance:
            return
        if instance.task:
            instance.task.cancel()
            try:
                await instance.task
            except asyncio.CancelledError:
                pass
        await instance.bot.delete_webhook(drop_pending_updates=False)
        await instance.bot.session.close()
        logger.info("Stopped child bot %s", bot_id)

    async def reload_bot(self, bot_id: int) -> None:
        bot_doc = await self._bot_repo.get_by_id(bot_id)
        if bot_doc and bot_doc.get("status") == "active":
            await self.start_bot(bot_doc)
        else:
            await self.stop_bot(bot_id)

    async def shutdown(self) -> None:
        for bot_id in list(self._instances.keys()):
            await self.stop_bot(bot_id)
