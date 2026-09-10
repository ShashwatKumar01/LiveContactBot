import asyncio
import logging

from aiohttp import web

logger = logging.getLogger(__name__)


def setup_child_webhook_route(app: web.Application, bot_manager, settings) -> None:
    """One route for all child bots — supports adding bots after the server is running."""

    async def child_webhook(request: web.Request) -> web.Response:
        try:
            bot_id = int(request.match_info["bot_id"])
        except (KeyError, ValueError, TypeError):
            return web.Response(status=404, text="Invalid bot id")

        if settings.webhook_secret:
            secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if secret != settings.webhook_secret:
                return web.Response(status=401, text="Unauthorized")

        instance = bot_manager.instances.get(bot_id)
        if not instance:
            bot_repo = request.app["bot_repo"]
            owner_alerts = request.app["owner_alerts"]
            master_bot = request.app["master_bot"]
            bot_doc = await bot_repo.get_by_id(bot_id)
            if bot_doc and bot_doc.get("status") == "active":
                try:
                    await bot_manager.start_bot(bot_doc)
                    instance = bot_manager.instances.get(bot_id)
                    logger.info("Auto-restarted child bot %s from webhook", bot_id)
                except Exception as e:
                    logger.error("Auto-restart failed for bot %s: %s", bot_id, e)
                    await owner_alerts.notify_once(
                        master_bot,
                        bot_doc["owner_id"],
                        bot_id,
                        bot_doc.get("username") or "bot",
                        "offline",
                        "Your bot stopped responding on the server and could not be restarted automatically. "
                        "Try /mybots → disconnect and add the bot again.",
                    )
            if not instance:
                logger.warning("Webhook for unknown or stopped child bot %s", bot_id)
                return web.Response(status=404, text="Bot not running")

        bot = instance.bot
        dp = instance.dispatcher
        try:
            update = await request.json(loads=bot.session.json_loads)
        except Exception:
            return web.Response(status=400, text="Bad request")

        async def process() -> None:
            try:
                await dp.feed_webhook_update(bot, update)
            except Exception as e:
                logger.exception("Child bot %s webhook error: %s", bot_id, e)
                bot_repo = request.app["bot_repo"]
                bot_doc = await bot_repo.get_by_id(bot_id)
                if bot_doc:
                    await request.app["owner_alerts"].notify_once(
                        request.app["master_bot"],
                        bot_doc["owner_id"],
                        bot_id,
                        bot_doc.get("username") or "bot",
                        "handler_error",
                        "Your bot hit an internal error while handling a message. "
                        "If this keeps happening, reconnect the bot from /mybots.",
                    )

        asyncio.create_task(process())
        return web.json_response({}, dumps=bot.session.json_dumps)

    app.router.add_route("POST", "/webhook/child/{bot_id}", child_webhook)
