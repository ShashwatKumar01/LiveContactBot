from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.web.admin_routes import setup_web_admin
from app.web.child_webhook import setup_child_webhook_route


def create_web_app(
    settings,
    master_dp,
    master_bot,
    bot_manager,
    bot_repo,
    owner_repo,
    user_repo,
    broadcast_repo,
    subscription_repo,
    app_settings_repo,
    owner_alerts,
) -> web.Application:
    app = web.Application()
    app["settings"] = settings
    app["bot_manager"] = bot_manager
    app["owner_alerts"] = owner_alerts
    app["bot_repo"] = bot_repo
    app["owner_repo"] = owner_repo
    app["user_repo"] = user_repo
    app["broadcast_repo"] = broadcast_repo
    app["subscription_repo"] = subscription_repo
    app["app_settings_repo"] = app_settings_repo
    app["master_bot"] = master_bot

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "contactbot"})

    app.router.add_get("/health", health)
    setup_web_admin(app)

    webhook_handler = SimpleRequestHandler(
        dispatcher=master_dp,
        bot=master_bot,
        secret_token=settings.webhook_secret,
    )
    webhook_handler.register(app, path=settings.webhook_path)

    setup_child_webhook_route(app, bot_manager, settings)

    setup_application(app, master_dp, bot=master_bot)
    return app
