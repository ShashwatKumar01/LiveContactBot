"""
ContactBot — Livegram-style feedback bot builder.

Usage:
    python contact.py

Web admin panel: http://localhost:8080/admin
"""
import asyncio
import logging
import signal
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.core.config import get_settings
from app.database.connection import db_manager
from app.database.repositories import (
    BotRepository,
    OwnerRepository,
    BotUserRepository,
    MessageMapRepository,
    BroadcastRepository,
    SubscriptionRepository,
)
from app.bot.master.handlers import create_master_router
from app.bot.master.plan import create_plan_router
from app.bot.master.superadmin import create_superadmin_router
from app.bot.master.middleware import MasterMiddleware
from app.services.bot_manager import BotManager
from app.services.entitlement_service import EntitlementService
from app.workers.broadcast_worker import BroadcastWorker
from app.web.app_factory import create_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("contactbot")


async def main() -> None:
    settings = get_settings()

    await db_manager.connect(settings.mongodb_uri, settings.mongodb_database)
    if "railway.internal" in settings.mongodb_uri:
        logger.warning(
            "Using Railway internal MongoDB. If you see OutOfDiskSpace (14031), "
            "switch to MongoDB Atlas — see DEPLOY_ATLAS.md"
        )
    await db_manager.create_indexes()
    db = db_manager.db

    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis)

    bot_repo = BotRepository(db)
    owner_repo = OwnerRepository(db)
    user_repo = BotUserRepository(db)
    msg_map_repo = MessageMapRepository(db)
    broadcast_repo = BroadcastRepository(db)
    subscription_repo = SubscriptionRepository(db)
    await subscription_repo.seed_default_plans()

    entitlement = EntitlementService(
        settings=settings,
        subscription_repo=subscription_repo,
        bot_repo=bot_repo,
        broadcast_repo=broadcast_repo,
        owner_repo=owner_repo,
    )

    bot_manager = BotManager(
        settings=settings,
        redis=redis,
        bot_repo=bot_repo,
        owner_repo=owner_repo,
        user_repo=user_repo,
        msg_map_repo=msg_map_repo,
        broadcast_repo=broadcast_repo,
        entitlement=entitlement,
    )

    broadcast_worker = BroadcastWorker(
        settings=settings,
        bot_repo=bot_repo,
        user_repo=user_repo,
        broadcast_repo=broadcast_repo,
        owner_repo=owner_repo,
    )
    worker_task = asyncio.create_task(broadcast_worker.start())

    master_bot = Bot(
        token=settings.master_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    master_dp = Dispatcher(storage=storage)

    master_middleware = MasterMiddleware(
        settings=settings,
        bot_repo=bot_repo,
        owner_repo=owner_repo,
        user_repo=user_repo,
        broadcast_repo=broadcast_repo,
        subscription_repo=subscription_repo,
        entitlement=entitlement,
        bot_manager=bot_manager,
    )
    master_dp.message.middleware(master_middleware)
    master_dp.callback_query.middleware(master_middleware)
    master_dp.include_router(create_superadmin_router(settings))
    master_dp.include_router(create_plan_router())
    master_dp.include_router(create_master_router())

    me = await master_bot.get_me()
    logger.info("Master bot @%s started", me.username)

    web_app = create_web_app(
        settings=settings,
        master_dp=master_dp,
        master_bot=master_bot,
        bot_manager=bot_manager,
        bot_repo=bot_repo,
        owner_repo=owner_repo,
        user_repo=user_repo,
        broadcast_repo=broadcast_repo,
        subscription_repo=subscription_repo,
    )
    bot_manager.attach_web_app(web_app)
    await bot_manager.start_all()
    from app.web.app_factory import register_child_webhook

    for instance in bot_manager.instances.values():
        register_child_webhook(web_app, settings, instance)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.app_host, settings.app_port)
    await site.start()
    logger.info("Web admin panel: http://%s:%s/admin", settings.app_host, settings.app_port)

    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        shutdown_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        if settings.is_production:
            if not settings.webhook_host:
                raise RuntimeError("WEBHOOK_HOST is required when ENVIRONMENT=production")
            webhook_url = f"{settings.webhook_host.rstrip('/')}{settings.webhook_path}"
            await master_bot.set_webhook(
                url=webhook_url,
                secret_token=settings.webhook_secret,
            )
            logger.info("Webhook mode: %s", webhook_url)
            await shutdown_event.wait()
        else:
            logger.info("Polling mode (development)")
            await master_dp.start_polling(master_bot, handle_signals=True)
    finally:
        broadcast_worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await bot_manager.shutdown()
        await master_bot.session.close()
        await runner.cleanup()
        await redis.close()
        await db_manager.disconnect()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
