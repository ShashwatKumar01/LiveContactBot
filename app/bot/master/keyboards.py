from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.master.keyboard_style import styled_btn


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        styled_btn("➕ Add Bot", "add_bot", ButtonStyle.primary),
        styled_btn("🤖 My Bots", "my_bots", ButtonStyle.primary),
    )
    b.row(styled_btn("❓ Help", "help"))
    return b.as_markup()


def bots_list_kb(bots: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bot in bots:
        username = bot.get("username", "unknown")
        status = "🟢" if bot.get("status") == "active" else "🔴"
        b.row(styled_btn(f"{status} @{username}", f"bot:{bot['bot_id']}"))
    b.row(styled_btn("➕ Add Bot", "add_bot", ButtonStyle.primary))
    b.row(styled_btn("« Back", "back_main"))
    return b.as_markup()


def bot_settings_kb(bot_doc: dict) -> InlineKeyboardMarkup:
    bot_id = bot_doc["bot_id"]
    anonymous = bot_doc.get("anonymous", False)
    anon_label = "On" if anonymous else "Off"
    auto_on = bot_doc.get("auto_reply_enabled", False)
    auto_label = "On" if auto_on else "Off"
    notify_in = "On" if bot_doc.get("notify_received", False) else "Off"
    notify_reply = "On" if bot_doc.get("notify_reply_sent", False) else "Off"
    cd_min = int(bot_doc.get("auto_reply_cooldown_seconds", 3600) // 60)

    b = InlineKeyboardBuilder()
    b.row(
        styled_btn("📝 Texts", f"bot_texts:{bot_id}", ButtonStyle.primary),
        styled_btn("👥 Groups", f"groups:{bot_id}", ButtonStyle.primary),
    )
    b.row(
        styled_btn("📢 Broadcast", f"bc_start:{bot_id}", ButtonStyle.success),
        styled_btn("📊 Statistics", f"stats:{bot_id}", ButtonStyle.success),
    )
    b.row(
        styled_btn(f"🤖 Auto-reply: {auto_label}", f"toggle_auto_reply:{bot_id}"),
        styled_btn(f"⏱ Cooldown: {cd_min}m", f"auto_cd_menu:{bot_id}"),
    )
    b.row(
        styled_btn(f"📥 Sent notice: {notify_in}", f"toggle_notify_received:{bot_id}"),
        styled_btn(f"📤 Reply notice: {notify_reply}", f"toggle_notify_reply:{bot_id}"),
    )
    b.row(styled_btn(f"🕶 Anonymous: {anon_label}", f"toggle_anon:{bot_id}"))
    b.row(styled_btn("🔌 Disconnect Bot", f"disconnect:{bot_id}", ButtonStyle.danger))
    b.row(styled_btn("« Back to Bots List", "my_bots"))
    return b.as_markup()


def bot_texts_kb(bot_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(styled_btn("Welcome (/start)", f"text_edit:{bot_id}:start", ButtonStyle.primary))
    b.row(styled_btn("Auto-reply message", f"text_edit:{bot_id}:auto_reply"))
    b.row(
        styled_btn("“Sent to admin”", f"text_edit:{bot_id}:received"),
        styled_btn("“Reply sent”", f"text_edit:{bot_id}:reply_sent"),
    )
    b.row(styled_btn("« Back", f"bot:{bot_id}"))
    return b.as_markup()


def auto_cooldown_kb(bot_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        styled_btn("30 min", f"auto_cd_set:{bot_id}:1800"),
        styled_btn("1 hour", f"auto_cd_set:{bot_id}:3600", ButtonStyle.primary),
        styled_btn("2 hours", f"auto_cd_set:{bot_id}:7200"),
    )
    b.row(
        styled_btn("6 hours", f"auto_cd_set:{bot_id}:21600"),
        styled_btn("24 hours", f"auto_cd_set:{bot_id}:86400"),
    )
    b.row(styled_btn("« Back", f"bot:{bot_id}"))
    return b.as_markup()


def broadcast_stop_kb(job_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(styled_btn("⏹ Stop broadcast", f"bc_stop:{job_id}", ButtonStyle.danger))
    return b.as_markup()


def broadcast_audience_kb(bot_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(styled_btn("All users", f"bc_aud:{bot_id}:all", ButtonStyle.primary))
    b.row(
        styled_btn("Active (30 days)", f"bc_aud:{bot_id}:active"),
        styled_btn("With username", f"bc_aud:{bot_id}:username"),
    )
    b.row(styled_btn("« Cancel", f"bc_cancel:{bot_id}", ButtonStyle.danger))
    return b.as_markup()


def confirm_disconnect_kb(bot_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        styled_btn("✅ Yes, disconnect", f"confirm_disconnect:{bot_id}", ButtonStyle.danger),
        styled_btn("❌ Cancel", f"bot:{bot_id}"),
    )
    return b.as_markup()
