import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.core.constants import DEFAULT_LOCALES
from app.database.repositories import AppSettingsRepository, BotUserRepository, BroadcastRepository
from app.bot.master.keyboards import broadcast_stop_kb
from app.bot.shared.broadcast_stop import create_broadcast_stop_router
from app.services.broadcast_progress import format_progress_text
from app.services.entitlement_service import EntitlementService
from app.bot.child.auto_reply import maybe_send_auto_reply
from app.services.child_start_text import (
    append_promo_footer,
    apply_user_template_vars,
    get_locale_start,
)
from app.services.relay_service import RelayService

# Broadcast is configured from the master bot (My Bots → Broadcast).

logger = logging.getLogger(__name__)


def create_child_router() -> Router:
    router = Router()

    @router.message(CommandStart(), F.chat.type == "private")
    async def cmd_start(
        message: Message,
        bot_doc: dict,
        app_settings: AppSettingsRepository,
        entitlement: EntitlementService,
    ) -> None:
        text = apply_user_template_vars(get_locale_start(bot_doc, None), message.from_user)
        if await entitlement.shows_child_promo_branding(bot_doc["owner_id"]):
            footer = await app_settings.get_child_start_promo_footer()
            text = append_promo_footer(text, footer)
        try:
            await message.answer(text, parse_mode="HTML")
        except TelegramBadRequest:
            logger.warning("Child /start HTML parse failed for bot %s", bot_doc["bot_id"])
            await message.answer(text, parse_mode=None)

    @router.message(Command("broadcast"))
    async def cmd_broadcast(
        message: Message,
        bot_doc: dict,
        broadcast_repo: BroadcastRepository,
        entitlement: EntitlementService,
    ) -> None:
        if not message.from_user or message.from_user.id != bot_doc["owner_id"]:
            return
        if not message.reply_to_message:
            await message.answer("Reply to a forwarded user message with /broadcast.")
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
        await broadcast_repo.update_job(
            job_id,
            status="pending",
            progress_via_master=False,
        )
        progress = await message.answer(
            format_progress_text(
                {
                    "job_id": job_id,
                    "status": "pending",
                    "total": 0,
                    "sent": 0,
                    "failed": 0,
                }
            ),
            reply_markup=broadcast_stop_kb(job_id),
        )
        await broadcast_repo.update_job(
            job_id,
            progress_chat_id=message.chat.id,
            progress_message_id=progress.message_id,
        )

    @router.message(F.chat.type == "private", ~Command())
    async def handle_private_message(
        message: Message,
        bot: Bot,
        bot_doc: dict,
        relay: RelayService,
        user_repo: BotUserRepository,
    ) -> None:
        if not message.from_user:
            return

        user_id = message.from_user.id
        bot_id = bot_doc["bot_id"]
        owner_id = bot_doc["owner_id"]

        if relay.is_admin_message(bot_doc, user_id, message.chat.id):
            if message.reply_to_message:
                success = await relay.relay_admin_to_user(bot, bot_doc, message)
                if not success:
                    await message.reply(
                        "❌ Could not deliver reply. Reply to a forwarded user message."
                    )
                elif bot_doc.get("notify_reply_sent", False):
                    locales = bot_doc.get("locales", DEFAULT_LOCALES)
                    text = locales.get("en", DEFAULT_LOCALES["en"]).get("reply_sent", "")
                    if text:
                        await message.reply(text)
            elif user_id == owner_id:
                await message.answer(
                    "Reply to a user's message (above) to answer them. "
                    "Use /start to see the welcome text users get."
                )
            return

        if user_id == owner_id:
            return

        if not relay.is_supported_message(message):
            await message.answer("❌ This message type is not supported.")
            return

        if not await relay.relay_user_to_admin(bot, bot_doc, message):
            await message.answer(
                "❌ Could not deliver your message. Please try again or send a different format."
            )
            return
        await maybe_send_auto_reply(bot, bot_doc, user_repo, message)

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

    router.include_router(create_broadcast_stop_router())
    return router
