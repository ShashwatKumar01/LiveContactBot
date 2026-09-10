from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.web.admin_routes import setup_web_admin

_CHILD_PATHS_KEY = "_registered_child_webhook_paths"


def register_child_webhook(
    app: web.Application,
    settings,
    instance,
) -> None:
    """Register aiohttp route for a child bot (production webhooks)."""
    paths: set[str] = app.setdefault(_CHILD_PATHS_KEY, set())
    path = f"/webhook/child/{instance.bot_id}"
    if path in paths:
        return
    child_handler = SimpleRequestHandler(
        dispatcher=instance.dispatcher,
        bot=instance.bot,
        secret_token=settings.webhook_secret,
    )
    child_handler.register(app, path=path)
    paths.add(path)


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
) -> web.Application:
    app = web.Application()
    app["settings"] = settings
    app["bot_manager"] = bot_manager
    app["bot_repo"] = bot_repo
    app["owner_repo"] = owner_repo
    app["user_repo"] = user_repo
    app["broadcast_repo"] = broadcast_repo
    app["subscription_repo"] = subscription_repo

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

    for instance in bot_manager.instances.values():
        register_child_webhook(app, settings, instance)

    setup_application(app, master_dp, bot=master_bot)
    return app
