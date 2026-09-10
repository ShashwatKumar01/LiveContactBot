import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.core.constants import DEFAULT_LOCALES
from app.database.repositories import AppSettingsRepository, BroadcastRepository
from app.services.child_start_text import (
    append_promo_footer,
    apply_user_template_vars,
    get_locale_start,
)
from app.services.entitlement_service import EntitlementService
from app.services.relay_service import RelayService

logger = logging.getLogger(__name__)


def create_child_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def cmd_start(
        message: Message,
        bot_doc: dict,
        app_settings: AppSettingsRepository,
        entitlement: EntitlementService,
    ) -> None:
        lang = message.from_user.language_code if message.from_user else None
        text = apply_user_template_vars(
            get_locale_start(bot_doc, lang),
            message.from_user,
        )
        if await entitlement.shows_child_promo_branding(bot_doc["owner_id"]):
            footer = await app_settings.get_child_start_promo_footer()
            text = append_promo_footer(text, footer)
        await message.answer(text)

    @router.message(Command("broadcast"))
    async def cmd_broadcast(
        message: Message,
        bot_doc: dict,
        broadcast_repo: BroadcastRepository,
        entitlement: EntitlementService,
    ) -> None:
        if not message.from_user:
            return
        if message.from_user.id != bot_doc["owner_id"]:
            return
        if not message.reply_to_message:
            await message.answer(
                "Reply to a message with /broadcast to send it to all bot users."
            )
            return

        allowed, reason = await entitlement.can_broadcast(message.from_user.id)
        if not allowed:
            await message.answer(f"❌ {reason}")
            return

        job_id = await broadcast_repo.create_job(
            bot_id=bot_doc["bot_id"],
            owner_id=bot_doc["owner_id"],
            source_chat_id=message.chat.id,
            source_msg_id=message.reply_to_message.message_id,
        )
        await broadcast_repo.update_job(job_id, status="pending")
        await message.answer(
            f"📢 Broadcast queued (job <code>{job_id[:8]}</code>). "
            "Recipients are being prepared..."
        )

    @router.message(F.chat.type == "private")
    async def handle_private_message(
        message: Message,
        bot: Bot,
        bot_doc: dict,
        relay: RelayService,
    ) -> None:
        if not message.from_user:
            return

        user_id = message.from_user.id
        bot_id = bot_doc["bot_id"]
        owner_id = bot_doc["owner_id"]

        if relay.is_admin_message(bot_doc, user_id, message.chat.id):
            if message.reply_to_message:
                success = await relay.relay_admin_to_user(bot, bot_doc, message)
                if success and bot_doc.get("notify_reply_sent", False):
                    locales = bot_doc.get("locales", DEFAULT_LOCALES)
                    default = bot_doc.get("default_locale", "en")
                    text = locales.get(default, DEFAULT_LOCALES["en"]).get("reply_sent", "")
                    if text:
                        await message.reply(text)
                else:
                    await message.reply("❌ Could not deliver reply. User may have blocked the bot.")
            return

        if user_id == owner_id:
            return

        if not relay.is_supported_message(message):
            await message.answer("❌ This message type is not supported.")
            return

        await relay.relay_user_to_admin(bot, bot_doc, message)

    @router.message(F.chat.type.in_({"group", "supergroup"}))
    async def handle_group_message(
        message: Message,
        bot: Bot,
        bot_doc: dict,
        relay: RelayService,
    ) -> None:
        if not message.from_user or not bot_doc.get("group_id"):
            return
        if message.chat.id != bot_doc["group_id"]:
            return

        if message.reply_to_message:
            await relay.relay_admin_to_user(bot, bot_doc, message)

    return router
