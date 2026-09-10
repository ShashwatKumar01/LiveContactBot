import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.bot.filters.is_superadmin import IsSuperAdmin
from app.bot.master.superadmin_keyboards import (
    superadmin_main_kb,
    superadmin_bots_kb,
    superadmin_bot_detail_kb,
    superadmin_owners_kb,
    superadmin_owner_detail_kb,
    broadcast_confirm_kb,
)
from app.core.config import Settings
from app.database.repositories import (
    BotRepository,
    OwnerRepository,
    BotUserRepository,
    BroadcastRepository,
    SubscriptionRepository,
)
from app.services.bot_manager import BotManager

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


class MasterBroadcastStates(StatesGroup):
    choosing_target = State()
    composing = State()


def create_superadmin_router(settings: Settings) -> Router:
    router = Router()
    router.message.filter(IsSuperAdmin(settings))
    router.callback_query.filter(IsSuperAdmin(settings))

    @router.message(Command("admin"))
    async def cmd_admin(message: Message, settings: Settings) -> None:
        web_hint = f"\n\n🌐 Web panel: <code>http://localhost:{settings.app_port}/admin</code>"
        await message.answer(
            "👑 <b>Super Admin Panel</b>\n\nManage the entire ContactBot system." + web_hint,
            reply_markup=superadmin_main_kb(),
        )

    @router.callback_query(F.data == "sa:main")
    async def cb_main(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            "👑 <b>Super Admin Panel</b>\n\nManage the entire ContactBot system.",
            reply_markup=superadmin_main_kb(),
        )
        await callback.answer()

    @router.callback_query(F.data == "sa:stats")
    async def cb_stats(
        callback: CallbackQuery,
        bot_repo: BotRepository,
        owner_repo: OwnerRepository,
        user_repo: BotUserRepository,
        bot_manager: BotManager,
        subscription_repo: SubscriptionRepository,
    ) -> None:
        global_stats = await bot_repo.get_global_stats()
        text = (
            "📊 <b>System Statistics</b>\n\n"
            f"👥 Owners: <b>{await owner_repo.count()}</b>\n"
            f"⭐ Premium: <b>{await subscription_repo.count_premium_owners()}</b>\n"
            f"🤖 Active bots: <b>{await bot_repo.count_all('active')}</b>\n"
            f"🤖 Total bots: <b>{await bot_repo.count_all()}</b>\n"
            f"🟢 Running instances: <b>{len(bot_manager.instances)}</b>\n"
            f"👤 End-users (all bots): <b>{await user_repo.count_all()}</b>\n"
            f"📥 Total incoming: <b>{global_stats['incoming']}</b>\n"
            f"📤 Total outgoing: <b>{global_stats['outgoing']}</b>"
        )
        await callback.message.edit_text(text, reply_markup=superadmin_main_kb())
        await callback.answer()

    @router.callback_query(F.data.startswith("sa:bots:"))
    async def cb_bots_list(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        page = int(callback.data.split(":")[2])
        skip = page * PAGE_SIZE
        bots = await bot_repo.get_all(skip=skip, limit=PAGE_SIZE + 1)
        has_more = len(bots) > PAGE_SIZE
        bots = bots[:PAGE_SIZE]
        if not bots and page == 0:
            await callback.message.edit_text(
                "No bots registered yet.", reply_markup=superadmin_main_kb()
            )
        else:
            await callback.message.edit_text(
                f"<b>All Bots</b> (page {page + 1})",
                reply_markup=superadmin_bots_kb(bots, page, has_more),
            )
        await callback.answer()

    @router.callback_query(F.data.startswith("sa:bot:"))
    async def cb_bot_detail(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        bot_id = int(callback.data.split(":")[2])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc:
            await callback.answer("Bot not found.", show_alert=True)
            return
        stats = bot_doc.get("stats", {})
        text = (
            f"🤖 <b>@{bot_doc.get('username')}</b>\n\n"
            f"ID: <code>{bot_id}</code>\n"
            f"Owner: <code>{bot_doc.get('owner_id')}</code>\n"
            f"Status: <b>{bot_doc.get('status')}</b>\n"
            f"Users: {stats.get('total_users', 0)}\n"
            f"Incoming: {stats.get('incoming_messages', 0)}\n"
            f"Outgoing: {stats.get('outgoing_messages', 0)}"
        )
        await callback.message.edit_text(
            text,
            reply_markup=superadmin_bot_detail_kb(bot_id, bot_doc.get("status", "")),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("sa:disable:"))
    async def cb_disable_bot(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        bot_id = int(callback.data.split(":")[2])
        await bot_repo.admin_disable(bot_id, reason="Disabled by super admin")
        await bot_manager.stop_bot(bot_id)
        await callback.answer("Bot disabled.")
        bot_doc = await bot_repo.get_by_id(bot_id)
        if bot_doc:
            await callback.message.edit_reply_markup(
                reply_markup=superadmin_bot_detail_kb(bot_id, "disabled")
            )

    @router.callback_query(F.data.startswith("sa:enable:"))
    async def cb_enable_bot(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        bot_id = int(callback.data.split(":")[2])
        await bot_repo.admin_enable(bot_id)
        bot_doc = await bot_repo.get_by_id(bot_id)
        if bot_doc:
            await bot_manager.start_bot(bot_doc)
        await callback.answer("Bot enabled.")
        await callback.message.edit_reply_markup(
            reply_markup=superadmin_bot_detail_kb(bot_id, "active")
        )

    @router.callback_query(F.data.startswith("sa:owners:"))
    async def cb_owners_list(callback: CallbackQuery, owner_repo: OwnerRepository) -> None:
        page = int(callback.data.split(":")[2])
        skip = page * PAGE_SIZE
        owners = await owner_repo.get_all(skip=skip, limit=PAGE_SIZE + 1)
        has_more = len(owners) > PAGE_SIZE
        owners = owners[:PAGE_SIZE]
        await callback.message.edit_text(
            f"<b>All Owners</b> (page {page + 1})",
            reply_markup=superadmin_owners_kb(owners, page, has_more),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("sa:owner:"))
    async def cb_owner_detail(
        callback: CallbackQuery,
        owner_repo: OwnerRepository,
        bot_repo: BotRepository,
        subscription_repo: SubscriptionRepository,
        settings: Settings,
    ) -> None:
        owner_id = int(callback.data.split(":")[2])
        owner = await owner_repo.get(owner_id)
        bot_count = await bot_repo.count_by_owner(owner_id)
        plan_id = await subscription_repo.get_owner_plan_id(owner_id)
        is_premium = plan_id == "PREMIUM"
        max_bots = await owner_repo.get_max_bots(owner_id, settings.max_bots_free)
        banned = bool(owner and owner.get("banned"))
        text = (
            f"👤 <b>Owner</b> <code>{owner_id}</code>\n\n"
            f"Username: @{owner.get('username', '—') if owner else '—'}\n"
            f"Plan: <b>{plan_id}</b>\n"
            f"Banned: <b>{'Yes' if banned else 'No'}</b>\n"
            f"Active bots: {bot_count}\n"
            f"Max bots limit: {max_bots}\n\n"
            f"Grant premium: <code>/grantpremium {owner_id}</code>\n"
            f"Set limit: <code>/setlimit {owner_id} 10</code>"
        )
        await callback.message.edit_text(
            text,
            reply_markup=superadmin_owner_detail_kb(owner_id, banned, is_premium),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("sa:grant_premium:"))
    async def cb_grant_premium(callback: CallbackQuery, subscription_repo: SubscriptionRepository) -> None:
        owner_id = int(callback.data.split(":")[2])
        await subscription_repo.grant_premium(owner_id, granted_by=callback.from_user.id)
        await callback.answer("Premium granted!")
        await callback.message.edit_reply_markup(
            reply_markup=superadmin_owner_detail_kb(owner_id, False, True)
        )

    @router.callback_query(F.data.startswith("sa:revoke_premium:"))
    async def cb_revoke_premium(callback: CallbackQuery, subscription_repo: SubscriptionRepository) -> None:
        owner_id = int(callback.data.split(":")[2])
        await subscription_repo.revoke_premium(owner_id)
        await callback.answer("Premium revoked.")
        await callback.message.edit_reply_markup(
            reply_markup=superadmin_owner_detail_kb(owner_id, False, False)
        )

    @router.callback_query(F.data == "sa:premium")
    async def cb_premium(callback: CallbackQuery, subscription_repo: SubscriptionRepository) -> None:
        plans = await subscription_repo.get_all_plans()
        lines = []
        for p in plans:
            count = await subscription_repo.count_by_plan(p["_id"])
            lines.append(
                f"<b>{p['name']}</b> — {p['price_display']}\n"
                f"  Bots: {p['max_bots']} | Broadcasts/day: "
                f"{'∞' if p['broadcasts_per_day'] < 0 else p['broadcasts_per_day']}\n"
                f"  Active: {count}"
            )
        text = "⭐ <b>Premium Plans</b>\n\n" + "\n\n".join(lines)
        text += "\n\nGrant: <code>/grantpremium &lt;user_id&gt; [days]</code>"
        await callback.message.edit_text(text, reply_markup=superadmin_main_kb())
        await callback.answer()

    @router.callback_query(F.data.startswith("sa:ban:"))
    async def cb_ban_owner(
        callback: CallbackQuery, owner_repo: OwnerRepository, subscription_repo: SubscriptionRepository
    ) -> None:
        owner_id = int(callback.data.split(":")[2])
        await owner_repo.ban(owner_id, reason="Banned by super admin")
        is_premium = await subscription_repo.get_owner_plan_id(owner_id) == "PREMIUM"
        await callback.answer("Owner banned.")
        await callback.message.edit_reply_markup(
            reply_markup=superadmin_owner_detail_kb(owner_id, True, is_premium)
        )

    @router.callback_query(F.data.startswith("sa:unban:"))
    async def cb_unban_owner(
        callback: CallbackQuery, owner_repo: OwnerRepository, subscription_repo: SubscriptionRepository
    ) -> None:
        owner_id = int(callback.data.split(":")[2])
        await owner_repo.unban(owner_id)
        is_premium = await subscription_repo.get_owner_plan_id(owner_id) == "PREMIUM"
        await callback.answer("Owner unbanned.")
        await callback.message.edit_reply_markup(
            reply_markup=superadmin_owner_detail_kb(owner_id, False, is_premium)
        )

    @router.callback_query(F.data == "sa:restart")
    async def cb_restart_all(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        await bot_manager.shutdown()
        bots = await bot_repo.get_all_active()
        for bot_doc in bots:
            try:
                await bot_manager.start_bot(bot_doc)
            except Exception as e:
                logger.error("Restart failed for %s: %s", bot_doc.get("username"), e)
        await callback.answer(f"Restarted {len(bots)} bots.", show_alert=True)

    @router.callback_query(F.data == "sa:dbcheck")
    async def cb_dbcheck(
        callback: CallbackQuery,
        bot_repo: BotRepository,
        owner_repo: OwnerRepository,
        user_repo: BotUserRepository,
        broadcast_repo: BroadcastRepository,
    ) -> None:
        jobs = await broadcast_repo.get_running_jobs()
        text = (
            "🗄 <b>Raw DB Counts</b>\n\n"
            f"owners: {await owner_repo.count()}\n"
            f"bots: {await bot_repo.count_all()}\n"
            f"bot_users: {await user_repo.count_all()}\n"
            f"active broadcast jobs: {len(jobs)}"
        )
        await callback.message.edit_text(text, reply_markup=superadmin_main_kb())
        await callback.answer()

    @router.callback_query(F.data == "sa:broadcast")
    async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(MasterBroadcastStates.choosing_target)
        await callback.message.answer(
            "📢 <b>Master Broadcast</b>\n\n"
            "Choose target:\n"
            "• <code>owners</code> — all bot owners\n"
            "• <code>users</code> — all end-users across all bots\n\n"
            "Reply with <code>owners</code> or <code>users</code>"
        )
        await callback.answer()

    @router.message(MasterBroadcastStates.choosing_target)
    async def broadcast_choose_target(message: Message, state: FSMContext) -> None:
        target = (message.text or "").strip().lower()
        if target not in ("owners", "users"):
            await message.answer("Reply with <code>owners</code> or <code>users</code>")
            return
        await state.update_data(target=target)
        await state.set_state(MasterBroadcastStates.composing)
        await message.answer(
            f"Send the message to broadcast to <b>{target}</b> "
            "(text, photo, video, document, etc.):"
        )

    @router.message(MasterBroadcastStates.composing)
    async def broadcast_compose(
        message: Message,
        state: FSMContext,
        owner_repo: OwnerRepository,
        user_repo: BotUserRepository,
    ) -> None:
        data = await state.get_data()
        target = data.get("target", "owners")
        if target == "owners":
            count = await owner_repo.count()
        else:
            count = len(await user_repo.get_distinct_owner_user_ids())

        if count == 0:
            await message.answer("No recipients.")
            await state.clear()
            return

        await state.update_data(
            source_chat_id=message.chat.id,
            source_msg_id=message.message_id,
            recipient_count=count,
        )
        await message.answer(
            f"📊 Will send to <b>{count}</b> {target}.\nConfirm?",
            reply_markup=broadcast_confirm_kb(target),
        )

    @router.callback_query(F.data.startswith("sa:bc_confirm:"))
    async def broadcast_confirm(
        callback: CallbackQuery,
        state: FSMContext,
        broadcast_repo: BroadcastRepository,
        bot: Bot,
    ) -> None:
        target = callback.data.split(":")[2]
        data = await state.get_data()
        job_id = await broadcast_repo.create_system_job(
            owner_id=callback.from_user.id,
            source_chat_id=data["source_chat_id"],
            source_msg_id=data["source_msg_id"],
            target=f"all_{target}",
        )
        await state.clear()
        await callback.message.edit_text(
            f"🚀 Master broadcast started!\nJob: <code>{job_id[:8]}</code>\n"
            f"Recipients: {data.get('recipient_count', '?')}"
        )
        await callback.answer()

    @router.callback_query(F.data == "sa:bc_cancel")
    async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.edit_text("Broadcast cancelled.")
        await callback.answer()

    @router.message(Command("grantpremium"))
    async def cmd_grant_premium(
        message: Message, subscription_repo: SubscriptionRepository
    ) -> None:
        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("Usage: /grantpremium <user_id> [days]")
            return
        try:
            owner_id = int(parts[1])
            days = int(parts[2]) if len(parts) > 2 else None
        except ValueError:
            await message.answer("Invalid arguments.")
            return
        await subscription_repo.grant_premium(
            owner_id, days=days, granted_by=message.from_user.id
        )
        expiry = f" for {days} days" if days else " (lifetime)"
        await message.answer(f"⭐ Premium granted to <code>{owner_id}</code>{expiry}")

    @router.message(Command("revokepremium"))
    async def cmd_revoke_premium(
        message: Message, subscription_repo: SubscriptionRepository
    ) -> None:
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("Usage: /revokepremium <user_id>")
            return
        owner_id = int(parts[1])
        await subscription_repo.revoke_premium(owner_id)
        await message.answer(f"Premium revoked for <code>{owner_id}</code>")

    @router.message(Command("setlimit"))
    async def cmd_setlimit(
        message: Message, owner_repo: OwnerRepository
    ) -> None:
        parts = (message.text or "").split()
        if len(parts) != 3:
            await message.answer("Usage: /setlimit <user_id> <max_bots>")
            return
        try:
            user_id, limit = int(parts[1]), int(parts[2])
        except ValueError:
            await message.answer("Invalid arguments.")
            return
        await owner_repo.set_max_bots(user_id, limit)
        await message.answer(f"✅ User <code>{user_id}</code> max bots set to <b>{limit}</b>")

    @router.message(Command("disablebot"))
    async def cmd_disable_bot(
        message: Message, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("Usage: /disablebot <bot_id>")
            return
        bot_id = int(parts[1])
        await bot_repo.admin_disable(bot_id, reason="Disabled by super admin")
        await bot_manager.stop_bot(bot_id)
        await message.answer(f"⛔ Bot <code>{bot_id}</code> disabled.")

    @router.message(Command("enablebot"))
    async def cmd_enable_bot(
        message: Message, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("Usage: /enablebot <bot_id>")
            return
        bot_id = int(parts[1])
        await bot_repo.admin_enable(bot_id)
        bot_doc = await bot_repo.get_by_id(bot_id)
        if bot_doc:
            await bot_manager.start_bot(bot_doc)
        await message.answer(f"✅ Bot <code>{bot_id}</code> enabled.")

    return router
