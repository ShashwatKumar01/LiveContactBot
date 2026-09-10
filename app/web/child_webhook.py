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

        asyncio.create_task(process())
        return web.json_response({}, dumps=bot.session.json_dumps)

    app.router.add_route("POST", "/webhook/child/{bot_id}", child_webhook)
