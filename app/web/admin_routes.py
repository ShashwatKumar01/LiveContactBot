import pathlib

from aiohttp import web
import jinja2
import aiohttp_jinja2
from aiohttp_jinja2 import render_template

from app.web.auth import (
    SESSION_COOKIE,
    create_session_token,
    is_authenticated,
    require_auth,
)


def setup_web_admin(app: web.Application) -> None:
    template_dir = pathlib.Path(__file__).parent / "templates"
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(template_dir)))

    app.router.add_get("/admin/login", login_page)
    app.router.add_post("/admin/login", login_submit)
    app.router.add_get("/admin/logout", logout)
    app.router.add_get("/admin", require_auth(dashboard))
    app.router.add_get("/admin/owners", require_auth(owners_page))
    app.router.add_get("/admin/bots", require_auth(bots_page))
    app.router.add_get("/admin/premium", require_auth(premium_page))
    app.router.add_get("/admin/broadcast", require_auth(broadcast_page))
    app.router.add_post("/admin/broadcast", require_auth(broadcast_submit))
    app.router.add_post("/admin/restart", require_auth(restart_bots))
    app.router.add_post("/admin/owners/{owner_id}/premium", require_auth(grant_premium))
    app.router.add_post("/admin/owners/{owner_id}/free", require_auth(revoke_premium))
    app.router.add_post("/admin/owners/{owner_id}/ban", require_auth(ban_owner))
    app.router.add_post("/admin/owners/{owner_id}/unban", require_auth(unban_owner))
    app.router.add_post("/admin/bots/{bot_id}/disable", require_auth(disable_bot))
    app.router.add_post("/admin/bots/{bot_id}/enable", require_auth(enable_bot))
    app.router.add_post("/admin/premium/grant", require_auth(grant_premium_form))


async def login_page(request: web.Request) -> web.Response:
    secret = request.app["settings"].admin_web_secret
    if is_authenticated(request, secret):
        raise web.HTTPFound("/admin")
    return render_template("login.html", request, {})


async def login_submit(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    data = await request.post()
    password = data.get("password", "")
    if password != settings.admin_web_password:
        return render_template("login.html", request, {"error": "Invalid password"})
    token = create_session_token(settings.admin_web_secret)
    response = web.HTTPFound("/admin")
    response.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=86400 * 7)
    return response


async def logout(request: web.Request) -> web.Response:
    response = web.HTTPFound("/admin/login")
    response.del_cookie(SESSION_COOKIE)
    return response


async def dashboard(request: web.Request) -> web.Response:
    owner_repo = request.app["owner_repo"]
    bot_repo = request.app["bot_repo"]
    user_repo = request.app["user_repo"]
    subscription_repo = request.app["subscription_repo"]
    bot_manager = request.app["bot_manager"]
    global_stats = await bot_repo.get_global_stats()

    stats = {
        "owners": await owner_repo.count(),
        "active_bots": await bot_repo.count_all("active"),
        "premium": await subscription_repo.count_premium_owners(),
        "end_users": await user_repo.count_all(),
        "incoming": global_stats["incoming"],
        "running": len(bot_manager.instances),
    }
    flash = request.rel_url.query.get("flash", "")
    return render_template("dashboard.html", request, {"stats": stats, "flash": flash})


async def owners_page(request: web.Request) -> web.Response:
    owner_repo = request.app["owner_repo"]
    bot_repo = request.app["bot_repo"]
    subscription_repo = request.app["subscription_repo"]

    owners = await owner_repo.get_all(skip=0, limit=200)
    enriched = []
    for o in owners:
        tid = o["telegram_id"]
        plan_id = await subscription_repo.get_owner_plan_id(tid)
        enriched.append({
            **o,
            "plan_id": plan_id,
            "bot_count": await bot_repo.count_by_owner(tid),
        })

    flash = request.rel_url.query.get("flash", "")
    return render_template("owners.html", request, {"owners": enriched, "flash": flash})


async def bots_page(request: web.Request) -> web.Response:
    bot_repo = request.app["bot_repo"]
    bots = await bot_repo.get_all(skip=0, limit=200)
    flash = request.rel_url.query.get("flash", "")
    return render_template("bots.html", request, {"bots": bots, "flash": flash})


async def premium_page(request: web.Request) -> web.Response:
    subscription_repo = request.app["subscription_repo"]
    plans = await subscription_repo.get_all_plans()
    plan_counts = {p["_id"]: await subscription_repo.count_by_plan(p["_id"]) for p in plans}
    return render_template("premium.html", request, {"plans": plans, "plan_counts": plan_counts})


async def broadcast_page(request: web.Request) -> web.Response:
    owner_repo = request.app["owner_repo"]
    user_repo = request.app["user_repo"]
    flash = request.rel_url.query.get("flash", "")
    error = request.rel_url.query.get("error", "")
    return render_template(
        "broadcast.html",
        request,
        {
            "owner_count": await owner_repo.count(),
            "user_count": len(await user_repo.get_distinct_owner_user_ids()),
            "flash": flash,
            "error": error,
        },
    )


async def broadcast_submit(request: web.Request) -> web.Response:
    data = await request.post()
    target = data.get("target", "all_owners")
    message = (data.get("message") or "").strip()
    if not message:
        raise web.HTTPFound("/admin/broadcast?error=Message+is+required")

    broadcast_repo = request.app["broadcast_repo"]
    await broadcast_repo.create_text_job(
        bot_id=0,
        owner_id=0,
        text=message,
        target=target,
    )
    raise web.HTTPFound("/admin/broadcast?flash=Broadcast+queued+successfully")


async def restart_bots(request: web.Request) -> web.Response:
    bot_repo = request.app["bot_repo"]
    bot_manager = request.app["bot_manager"]
    await bot_manager.shutdown()
    for bot_doc in await bot_repo.get_all_active():
        try:
            await bot_manager.start_bot(bot_doc)
        except Exception:
            pass
    raise web.HTTPFound("/admin?flash=All+bots+restarted")


async def grant_premium(request: web.Request) -> web.Response:
    owner_id = int(request.match_info["owner_id"])
    subscription_repo = request.app["subscription_repo"]
    await subscription_repo.grant_premium(owner_id, granted_by=0)
    raise web.HTTPFound("/admin/owners?flash=Premium+granted")


async def revoke_premium(request: web.Request) -> web.Response:
    owner_id = int(request.match_info["owner_id"])
    subscription_repo = request.app["subscription_repo"]
    await subscription_repo.revoke_premium(owner_id)
    raise web.HTTPFound("/admin/owners?flash=Premium+revoked")


async def grant_premium_form(request: web.Request) -> web.Response:
    data = await request.post()
    owner_id = int(data.get("owner_id", 0))
    days_raw = data.get("days", "")
    days = int(days_raw) if days_raw else None
    subscription_repo = request.app["subscription_repo"]
    await subscription_repo.grant_premium(owner_id, days=days, granted_by=0)
    raise web.HTTPFound("/admin/premium")


async def ban_owner(request: web.Request) -> web.Response:
    owner_id = int(request.match_info["owner_id"])
    owner_repo = request.app["owner_repo"]
    await owner_repo.ban(owner_id, reason="Banned via web admin")
    raise web.HTTPFound("/admin/owners?flash=Owner+banned")


async def unban_owner(request: web.Request) -> web.Response:
    owner_id = int(request.match_info["owner_id"])
    owner_repo = request.app["owner_repo"]
    await owner_repo.unban(owner_id)
    raise web.HTTPFound("/admin/owners?flash=Owner+unbanned")


async def disable_bot(request: web.Request) -> web.Response:
    bot_id = int(request.match_info["bot_id"])
    bot_repo = request.app["bot_repo"]
    bot_manager = request.app["bot_manager"]
    await bot_repo.admin_disable(bot_id, reason="Disabled via web admin")
    await bot_manager.stop_bot(bot_id)
    raise web.HTTPFound("/admin/bots?flash=Bot+disabled")


async def enable_bot(request: web.Request) -> web.Response:
    bot_id = int(request.match_info["bot_id"])
    bot_repo = request.app["bot_repo"]
    bot_manager = request.app["bot_manager"]
    await bot_repo.admin_enable(bot_id)
    bot_doc = await bot_repo.get_by_id(bot_id)
    if bot_doc:
        await bot_manager.start_bot(bot_doc)
    raise web.HTTPFound("/admin/bots?flash=Bot+enabled")
