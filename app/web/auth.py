import hashlib
import hmac
import time
from aiohttp import web

SESSION_COOKIE = "cb_admin_session"
SESSION_TTL = 86400 * 7  # 7 days


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token(secret: str) -> str:
    ts = str(int(time.time()))
    sig = _sign(secret, ts)
    return f"{ts}.{sig}"


def verify_session_token(secret: str, token: str) -> bool:
    try:
        ts_str, sig = token.split(".", 1)
        if int(time.time()) - int(ts_str) > SESSION_TTL:
            return False
        return hmac.compare_digest(_sign(secret, ts_str), sig)
    except (ValueError, TypeError):
        return False


def is_authenticated(request: web.Request, secret: str) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    return bool(token and verify_session_token(secret, token))


def require_auth(handler):
    async def wrapper(request: web.Request):
        secret = request.app["settings"].admin_web_secret
        if not is_authenticated(request, secret):
            raise web.HTTPFound("/admin/login")
        return await handler(request)
    return wrapper
