import logging

from aiogram import Bot
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_ALERT_KINDS = ("offline", "handler_error", "poll_crashed", "start_failed", "delivery_failed")
_ALERT_TTL_SECONDS = 7 * 24 * 3600


class OwnerAlertService:
    """Notify bot owners via master bot, at most once per kind until bot restarts."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, bot_id: int, kind: str) -> str:
        return f"owner_alert:{bot_id}:{kind}"

    async def clear_bot(self, bot_id: int) -> None:
        for kind in _ALERT_KINDS:
            await self._redis.delete(self._key(bot_id, kind))

    async def notify_once(
        self,
        master_bot: Bot | None,
        owner_id: int,
        bot_id: int,
        username: str,
        kind: str,
        detail: str,
    ) -> bool:
        if not master_bot or not owner_id:
            return False
        key = self._key(bot_id, kind)
        if not await self._redis.set(key, "1", nx=True, ex=_ALERT_TTL_SECONDS):
            return False
        text = (
            f"⚠️ <b>Contact bot issue — @{username}</b>\n\n"
            f"{detail}\n\n"
            f"Open <b>/mybots</b> on the master bot to check settings. "
            f"You will not get this alert again until the bot is restarted successfully."
        )
        try:
            await master_bot.send_message(owner_id, text)
            return True
        except Exception as e:
            logger.warning("Could not DM owner %s for bot %s: %s", owner_id, bot_id, e)
            await self._redis.delete(key)
            return False
