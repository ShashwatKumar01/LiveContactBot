from aiogram import Bot
from aiogram.types import Message

from app.database.repositories import BotUserRepository
from app.services.child_start_text import apply_user_template_vars


async def maybe_send_auto_reply(
    bot: Bot,
    bot_doc: dict,
    user_repo: BotUserRepository,
    message: Message,
) -> None:
    if not bot_doc.get("auto_reply_enabled", False):
        return
    text = (bot_doc.get("auto_reply_text") or "").strip()
    if not text:
        locales = bot_doc.get("locales", {})
        text = (locales.get("en", {}) or {}).get("auto_reply", "").strip()
    if not text:
        return

    bot_id = bot_doc["bot_id"]
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    cooldown = int(bot_doc.get("auto_reply_cooldown_seconds", 3600))
    if cooldown > 0 and not await user_repo.should_send_auto_reply(bot_id, user_id, cooldown):
        return

    await message.answer(apply_user_template_vars(text, message.from_user))
    await user_repo.mark_auto_reply_sent(bot_id, user_id)
