import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.bot.master.keyboards import broadcast_audience_kb, bot_settings_kb, broadcast_stop_kb
from app.services.broadcast_progress import format_progress_text
from app.bot.master.states import BroadcastStates
from app.bot.telegram_utils import safe_edit_text
from app.database.repositories import BotRepository, BroadcastRepository, BotUserRepository
from app.services.entitlement_service import EntitlementService

logger = logging.getLogger(__name__)

AUDIENCE_LABELS = {
    "all": "all users",
    "active": "active users (30 days)",
    "username": "users with a username",
}


def create_broadcast_router() -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("bc_start:"))
    async def bc_start(
        callback: CallbackQuery,
        state: FSMContext,
        bot_repo: BotRepository,
        user_repo: BotUserRepository,
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        count = await user_repo.count_broadcast_audience(bot_id, "all")
        await safe_edit_text(
            callback.message,
            f"📢 <b>Broadcast for @{bot_doc.get('username')}</b>\n\n"
            f"Choose who should receive the post.\n"
            f"<i>{count} users</i> match “all users”.\n\n"
            "Type /cancel to abort.",
            reply_markup=broadcast_audience_kb(bot_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bc_cancel:"))
    async def bc_cancel(callback: CallbackQuery, state: FSMContext, bot_repo: BotRepository) -> None:
        await state.clear()
        if not callback.data or not callback.from_user:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc:
            await callback.answer()
            return
        username = bot_doc.get("username", "unknown")
        group = bot_doc.get("group_id")
        group_text = f"<code>{group}</code>" if group else "Not connected"
        text = (
            f"Here it is: <b>@{username}</b>\n\n"
            f"What do you want to do with the bot?\n\n"
            f"👥 Group: {group_text}"
        )
        await safe_edit_text(callback.message, text, reply_markup=bot_settings_kb(bot_doc))
        await callback.answer("Cancelled.")

    @router.callback_query(F.data.startswith("bc_aud:"))
    async def bc_audience(
        callback: CallbackQuery,
        state: FSMContext,
        bot_repo: BotRepository,
        user_repo: BotUserRepository,
        entitlement: EntitlementService,
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        parts = callback.data.split(":")
        bot_id, audience = int(parts[1]), parts[2]
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return

        allowed, reason = await entitlement.can_broadcast(callback.from_user.id)
        if not allowed:
            await callback.answer(reason, show_alert=True)
            return

        count = await user_repo.count_broadcast_audience(bot_id, audience)
        label = AUDIENCE_LABELS.get(audience, audience)
        await state.set_state(BroadcastStates.composing)
        await state.update_data(
            bot_id=bot_id,
            audience=audience,
            silent=False,
            messages=[],
        )
        await callback.message.answer(
            f"A broadcast post will be sent to <b>{count}</b> {label}.\n\n"
            "Send one or more messages to include in the post (text, photo, video, sticker, etc.). "
            "You can also forward from a channel.\n\n"
            "• <code>/silent</code> — send without notification sound\n"
            "• <code>/done</code> — queue broadcast\n"
            "• <code>/preview</code> — repeat last added message\n"
            "• <code>/cancel</code> — cancel",
        )
        await callback.answer()

    @router.message(BroadcastStates.composing, Command("cancel"))
    async def bc_cmd_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Broadcast cancelled.")

    @router.message(BroadcastStates.composing, Command("silent"))
    async def bc_cmd_silent(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        await state.update_data(silent=not data.get("silent", False))
        flag = "on" if not data.get("silent", False) else "off"
        await message.answer(f"🔕 Silent mode: <b>{flag}</b>")

    @router.message(BroadcastStates.composing, Command("done"))
    async def bc_cmd_done(
        message: Message,
        state: FSMContext,
        broadcast_repo: BroadcastRepository,
    ) -> None:
        data = await state.get_data()
        messages = data.get("messages") or []
        bot_id = data.get("bot_id")
        if not bot_id or not messages:
            await message.answer("Add at least one message before /done.")
            return
        if not message.from_user:
            return
        job_id = await broadcast_repo.create_compose_job(
            bot_id=bot_id,
            owner_id=message.from_user.id,
            messages=messages,
            audience=data.get("audience", "all"),
            silent=data.get("silent", False),
        )
        await broadcast_repo.update_job(
            job_id,
            status="pending",
            progress_via_master=True,
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
        await state.clear()

    @router.message(BroadcastStates.composing, Command("preview"))
    async def bc_cmd_preview(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        messages = data.get("messages") or []
        if not messages:
            await message.answer("Nothing to preview yet.")
            return
        last = messages[-1]
        await message.bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=last["chat_id"],
            message_id=last["message_id"],
        )

    @router.message(BroadcastStates.composing)
    async def bc_collect_message(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if message.text and message.text.strip().startswith("/"):
            return
        data = await state.get_data()
        messages = list(data.get("messages") or [])
        messages.append({"chat_id": message.chat.id, "message_id": message.message_id})
        await state.update_data(messages=messages)
        await message.answer(
            "✅ Message added to the post.\n"
            "Send more or type <code>/done</code> to queue the broadcast.",
        )

    return router
