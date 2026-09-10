import logging
import re

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.bot.master.keyboards import (
    main_menu_kb,
    bots_list_kb,
    bot_settings_kb,
    bot_texts_kb,
    auto_cooldown_kb,
    confirm_disconnect_kb,
)
from app.bot.master.states import AddBotStates, EditBotTextStates, SetGroupStates
from app.bot.master.broadcast_handlers import create_broadcast_router
from app.bot.shared.broadcast_stop import create_broadcast_stop_router
from app.core.config import Settings
from app.core.constants import MASTER_WELCOME
from app.core.crypto import encrypt_token
from app.database.repositories import BotRepository, OwnerRepository
from app.bot.telegram_utils import safe_edit_text
from app.services.bot_manager import BotManager
from app.services.entitlement_service import EntitlementService

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]+$")


def create_master_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def cmd_start(message: Message, owner_repo: OwnerRepository) -> None:
        if message.from_user:
            await owner_repo.upsert(
                message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )
        await message.answer(MASTER_WELCOME, reply_markup=main_menu_kb())

    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(
            "<b>ContactBot Help</b>\n\n"
            "1. Create a bot with @BotFather and get its token.\n"
            "2. Use /addbot and paste the token.\n"
            "3. Users message your bot — you receive messages in your chat with that bot.\n"
            "4. Reply to any forwarded message to respond.\n\n"
            "<b>Features:</b>\n"
            "• All media types supported\n"
            "• Connect a group for team replies\n"
            "• Broadcast to all users\n"
            "• Auto-reply with cooldown\n"
            "• Statistics"
        )

    @router.message(Command("addbot"))
    async def cmd_addbot(message: Message, state: FSMContext) -> None:
        await state.set_state(AddBotStates.waiting_for_token)
        await message.answer(
            "Send me your bot token from @BotFather.\n\n"
            "<i>Example: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz</i>"
        )

    @router.message(Command("mybots"))
    async def cmd_mybots(message: Message, bot_repo: BotRepository) -> None:
        if not message.from_user:
            return
        bots = await bot_repo.get_by_owner(message.from_user.id)
        active = [b for b in bots if b.get("status") == "active"]
        if not active:
            await message.answer("You have no connected bots yet.", reply_markup=main_menu_kb())
            return
        await message.answer(
            f"<b>Your bots ({len(active)}):</b>",
            reply_markup=bots_list_kb(active),
        )

    @router.callback_query(F.data == "back_main")
    async def cb_back_main(callback: CallbackQuery) -> None:
        await safe_edit_text(callback.message, MASTER_WELCOME, reply_markup=main_menu_kb())
        await callback.answer()

    @router.callback_query(F.data == "help")
    async def cb_help(callback: CallbackQuery) -> None:
        await safe_edit_text(
            callback.message,
            "<b>ContactBot Help</b>\n\n"
            "Create a bot with @BotFather, then add it here with /addbot.\n"
            "All user messages are forwarded to you. Reply to forward back.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()

    @router.callback_query(F.data == "add_bot")
    async def cb_add_bot(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AddBotStates.waiting_for_token)
        await callback.message.answer(
            "Send me your bot token from @BotFather.\n\n"
            "<i>Example: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz</i>"
        )
        await callback.answer()

    @router.callback_query(F.data == "my_bots")
    async def cb_my_bots(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        if not callback.from_user:
            return
        bots = await bot_repo.get_by_owner(callback.from_user.id)
        active = [b for b in bots if b.get("status") == "active"]
        if not active:
            await safe_edit_text(
                callback.message,
                "You have no connected bots yet.",
                reply_markup=main_menu_kb(),
            )
        else:
            await safe_edit_text(
                callback.message,
                f"<b>Your bots ({len(active)}):</b>",
                reply_markup=bots_list_kb(active),
            )
        await callback.answer()

    @router.message(AddBotStates.waiting_for_token)
    async def process_token(
        message: Message,
        state: FSMContext,
        bot: Bot,
        settings: Settings,
        bot_repo: BotRepository,
        owner_repo: OwnerRepository,
        entitlement: EntitlementService,
        bot_manager: BotManager,
    ) -> None:
        if not message.from_user or not message.text:
            return

        if await owner_repo.is_banned(message.from_user.id):
            await message.answer("❌ Your account is suspended. Contact support.")
            await state.clear()
            return

        token = message.text.strip()
        if not TOKEN_RE.match(token):
            await message.answer("❌ Invalid token format. Please send a valid bot token.")
            return

        test_bot = Bot(token=token)
        try:
            me = await test_bot.get_me()
        except Exception:
            await message.answer("❌ Invalid token. Could not connect to Telegram.")
            await test_bot.session.close()
            return
        await test_bot.session.close()

        encrypted = encrypt_token(token, settings.token_encryption_key)
        existing = await bot_repo.get_by_id(me.id)

        if not existing:
            allowed, reason = await entitlement.can_add_bot(message.from_user.id)
            if not allowed:
                await message.answer(f"❌ {reason}")
                await state.clear()
                return

        if existing:
            if existing.get("owner_id") != message.from_user.id:
                await message.answer("❌ This bot is registered to another account.")
                await state.clear()
                return
            bot_doc = await bot_repo.reactivate(
                bot_id=me.id,
                owner_id=message.from_user.id,
                token_encrypted=encrypted,
                username=me.username or "",
                first_name=me.first_name or "",
            )
            if not bot_doc:
                await message.answer("❌ Could not reconnect bot.")
                await state.clear()
                return
            restart_msg = "reconnected"
        else:
            bot_doc = await bot_repo.create(
                bot_id=me.id,
                owner_id=message.from_user.id,
                token_encrypted=encrypted,
                username=me.username or "",
                first_name=me.first_name or "",
            )
            restart_msg = "connected"

        try:
            await bot_manager.start_bot(bot_doc)
        except Exception as e:
            logger.exception("Failed to start bot @%s: %s", me.username, e)
            await bot_manager.stop_bot(me.id)
            await bot_repo.disconnect(me.id, message.from_user.id)
            await message.answer(
                "❌ Bot could not start. Check master bot logs or try again in a minute."
            )
            await state.clear()
            return

        await state.clear()
        await message.answer(
            f"✅ Bot <b>@{me.username}</b> {restart_msg} successfully!\n\n"
            f"Users can now message @{me.username} and you'll receive their messages here.\n"
            f"Use /mybots to manage settings.",
            reply_markup=bot_settings_kb(bot_doc),
        )

        try:
            await bot.send_message(
                message.from_user.id,
                f"ℹ️ Your contact bot @{me.username} is now active.\n"
                "Messages from users will appear in this chat.",
            )
        except Exception:
            pass

    @router.callback_query(F.data.startswith("bot:"))
    async def cb_bot_detail(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Bot not found.", show_alert=True)
            return

        username = bot_doc.get("username", "unknown")
        group = bot_doc.get("group_id")
        group_text = f"<code>{group}</code>" if group else "Not connected"
        text = (
            f"Here it is: <b>@{username}</b>\n\n"
            f"What do you want to do with the bot?\n\n"
            f"👥 Group: {group_text}"
        )
        await callback.message.edit_text(text, reply_markup=bot_settings_kb(bot_doc))
        await callback.answer()

    @router.callback_query(F.data.startswith("stats:"))
    async def cb_stats(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return

        stats = bot_doc.get("stats", {})
        text = (
            f"📊 <b>Statistics for @{bot_doc.get('username')}</b>\n\n"
            f"👥 Total users: <b>{stats.get('total_users', 0)}</b>\n"
            f"📥 Incoming messages: <b>{stats.get('incoming_messages', 0)}</b>\n"
            f"📤 Outgoing messages: <b>{stats.get('outgoing_messages', 0)}</b>"
        )
        await callback.message.edit_text(text, reply_markup=bot_settings_kb(bot_doc))
        await callback.answer()

    @router.callback_query(F.data.startswith("toggle_notify_received:"))
    async def cb_toggle_notify_received(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        new_val = not bot_doc.get("notify_received", False)
        await bot_repo.update(bot_id, notify_received=new_val)
        bot_doc["notify_received"] = new_val
        await bot_manager.reload_bot(bot_id)
        username = bot_doc.get("username", "unknown")
        group = bot_doc.get("group_id")
        group_text = f"<code>{group}</code>" if group else "Not connected"
        text = (
            f"Here it is: <b>@{username}</b>\n\n"
            f"What do you want to do with the bot?\n\n"
            f"👥 Group: {group_text}"
        )
        await safe_edit_text(callback.message, text, reply_markup=bot_settings_kb(bot_doc))
        await callback.answer(f"“Sent to admin” notice: {'On' if new_val else 'Off'}")

    @router.callback_query(F.data.startswith("toggle_notify_reply:"))
    async def cb_toggle_notify_reply(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        new_val = not bot_doc.get("notify_reply_sent", False)
        await bot_repo.update(bot_id, notify_reply_sent=new_val)
        bot_doc["notify_reply_sent"] = new_val
        await bot_manager.reload_bot(bot_id)
        username = bot_doc.get("username", "unknown")
        group = bot_doc.get("group_id")
        group_text = f"<code>{group}</code>" if group else "Not connected"
        text = (
            f"Here it is: <b>@{username}</b>\n\n"
            f"What do you want to do with the bot?\n\n"
            f"👥 Group: {group_text}"
        )
        await safe_edit_text(callback.message, text, reply_markup=bot_settings_kb(bot_doc))
        await callback.answer(f"“Reply sent” notice: {'On' if new_val else 'Off'}")

    @router.callback_query(F.data.startswith("disconnect:"))
    async def cb_disconnect(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        await callback.message.edit_text(
            f"Disconnect <b>@{bot_doc.get('username')}</b>?\n\n"
            "Users will no longer be able to contact you through this bot.",
            reply_markup=confirm_disconnect_kb(bot_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("confirm_disconnect:"))
    async def cb_confirm_disconnect(
        callback: CallbackQuery,
        bot_repo: BotRepository,
        bot_manager: BotManager,
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        success = await bot_repo.disconnect(bot_id, callback.from_user.id)
        if success:
            await bot_manager.stop_bot(bot_id)
            await callback.message.edit_text(
                "✅ Bot disconnected.", reply_markup=main_menu_kb()
            )
        else:
            await callback.answer("Failed to disconnect.", show_alert=True)
            return
        await callback.answer()

    @router.callback_query(F.data.startswith("groups:"))
    async def cb_groups(callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        await state.set_state(SetGroupStates.waiting_for_group_id)
        await state.update_data(bot_id=bot_id)
        await callback.message.answer(
            "👥 <b>Connect a Group</b>\n\n"
            "1. Add your bot to a group as admin.\n"
            "2. Send the group's chat ID here (use @getidsbot or forward a message).\n\n"
            "Send <code>0</code> to disconnect the group."
        )
        await callback.answer()

    @router.message(SetGroupStates.waiting_for_group_id)
    async def process_group_id(
        message: Message,
        state: FSMContext,
        bot: Bot,
        bot_repo: BotRepository,
        bot_manager: BotManager,
    ) -> None:
        if not message.from_user or not message.text:
            return

        data = await state.get_data()
        bot_id = data.get("bot_id")
        if not bot_id:
            await state.clear()
            return

        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != message.from_user.id:
            await state.clear()
            return

        try:
            group_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Please send a valid numeric chat ID.")
            return

        if group_id == 0:
            await bot_repo.update(bot_id, group_id=None)
            await bot_manager.reload_bot(bot_id)
            await message.answer("✅ Group disconnected.")
            await state.clear()
            return

        child_bot = bot_manager.get_bot(bot_id)
        if not child_bot:
            await message.answer("❌ Bot is not running.")
            await state.clear()
            return

        try:
            chat = await child_bot.get_chat(group_id)
            member = await child_bot.get_chat_member(group_id, bot_doc["bot_id"])
            if member.status not in ("administrator", "creator"):
                await message.answer("❌ Bot must be an admin in the group.")
                return
        except Exception:
            await message.answer("❌ Could not verify group. Make sure the bot is added as admin.")
            return

        await bot_repo.update(bot_id, group_id=group_id)
        bot_doc["group_id"] = group_id
        await bot_manager.reload_bot(bot_id)
        await message.answer(
            f"✅ Group <b>{chat.title}</b> connected!\n"
            "Messages will now be forwarded to the group.",
            reply_markup=bot_settings_kb(bot_doc),
        )
        await state.clear()

    @router.callback_query(F.data.startswith("bot_texts:"))
    async def cb_bot_texts(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        await safe_edit_text(
            callback.message,
            f"📝 <b>Texts for @{bot_doc.get('username')}</b>\n\n"
            "English only. Auto-reply is sent on user messages (not /start) when enabled.",
            reply_markup=bot_texts_kb(bot_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("text_edit:"))
    async def cb_text_edit(callback: CallbackQuery, state: FSMContext, bot_repo: BotRepository) -> None:
        if not callback.from_user or not callback.data:
            return
        parts = callback.data.split(":")
        bot_id, key = int(parts[1]), parts[2]
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        labels = {
            "start": "welcome /start text",
            "auto_reply": "auto-reply message (when Auto-reply is On)",
            "received": "“sent to admin” notice text",
            "reply_sent": "“reply sent” notice text",
        }
        await state.set_state(EditBotTextStates.waiting_for_value)
        await state.update_data(bot_id=bot_id, text_key=key)
        await callback.message.answer(
            f"Send the new <b>{labels.get(key, key)}</b>.\n"
            "HTML supported. Variables: <code>${firstName}</code> <code>${username}</code>\n"
            "/cancel to abort."
        )
        await callback.answer()

    @router.message(EditBotTextStates.waiting_for_value)
    async def process_text_edit(
        message: Message,
        state: FSMContext,
        bot_repo: BotRepository,
        bot_manager: BotManager,
    ) -> None:
        if not message.from_user or not message.text:
            return
        if message.text.strip().lower() == "/cancel":
            await state.clear()
            await message.answer("Cancelled.")
            return
        data = await state.get_data()
        bot_id = data.get("bot_id")
        key = data.get("text_key")
        if not bot_id or not key:
            await state.clear()
            return
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != message.from_user.id:
            await state.clear()
            return
        value = message.text.strip()
        if key == "auto_reply":
            await bot_repo.update(bot_id, auto_reply_text=value)
        else:
            locales = bot_doc.get("locales", {})
            if "en" not in locales:
                locales["en"] = {}
            locales["en"][key] = value
            await bot_repo.update(bot_id, locales=locales)
        await bot_manager.reload_bot(bot_id)
        await state.clear()
        await message.answer("✅ Saved.", reply_markup=bot_texts_kb(bot_id))

    @router.callback_query(F.data.startswith("toggle_auto_reply:"))
    async def cb_toggle_auto_reply(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        new_val = not bot_doc.get("auto_reply_enabled", False)
        await bot_repo.update(bot_id, auto_reply_enabled=new_val)
        bot_doc["auto_reply_enabled"] = new_val
        await bot_manager.reload_bot(bot_id)
        username = bot_doc.get("username", "unknown")
        group_text = (
            f"<code>{bot_doc.get('group_id')}</code>"
            if bot_doc.get("group_id")
            else "Not connected"
        )
        text = (
            f"Here it is: <b>@{username}</b>\n\n"
            f"What do you want to do with the bot?\n\n"
            f"👥 Group: {group_text}"
        )
        await safe_edit_text(callback.message, text, reply_markup=bot_settings_kb(bot_doc))
        await callback.answer(f"Auto-reply {'On' if new_val else 'Off'}")

    @router.callback_query(F.data.startswith("auto_cd_menu:"))
    async def cb_auto_cd_menu(callback: CallbackQuery, bot_repo: BotRepository) -> None:
        if not callback.data:
            return
        bot_id = int(callback.data.split(":")[1])
        await safe_edit_text(
            callback.message,
            "⏱ <b>Auto-reply cooldown</b>\n\n"
            "Same user won't get auto-reply again until this time passes.",
            reply_markup=auto_cooldown_kb(bot_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("auto_cd_set:"))
    async def cb_auto_cd_set(
        callback: CallbackQuery, bot_repo: BotRepository, bot_manager: BotManager
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        parts = callback.data.split(":")
        bot_id, seconds = int(parts[1]), int(parts[2])
        bot_doc = await bot_repo.get_by_id(bot_id)
        if not bot_doc or bot_doc["owner_id"] != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        await bot_repo.update(bot_id, auto_reply_cooldown_seconds=seconds)
        bot_doc["auto_reply_cooldown_seconds"] = seconds
        await bot_manager.reload_bot(bot_id)
        await callback.answer(f"Cooldown: {seconds // 60} min")
        username = bot_doc.get("username", "unknown")
        group_text = (
            f"<code>{bot_doc.get('group_id')}</code>"
            if bot_doc.get("group_id")
            else "Not connected"
        )
        text = (
            f"Here it is: <b>@{username}</b>\n\n"
            f"What do you want to do with the bot?\n\n"
            f"👥 Group: {group_text}"
        )
        await safe_edit_text(callback.message, text, reply_markup=bot_settings_kb(bot_doc))

    router.include_router(create_broadcast_router())
    router.include_router(create_broadcast_stop_router())
    return router
