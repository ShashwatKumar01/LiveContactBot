from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Add Bot", callback_data="add_bot"))
    builder.row(InlineKeyboardButton(text="🤖 My Bots", callback_data="my_bots"))
    builder.row(InlineKeyboardButton(text="❓ Help", callback_data="help"))
    return builder.as_markup()


def bots_list_kb(bots: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bots:
        username = b.get("username", "unknown")
        status = "🟢" if b.get("status") == "active" else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} @{username}",
                callback_data=f"bot:{b['bot_id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="➕ Add Bot", callback_data="add_bot"))
    builder.row(InlineKeyboardButton(text="« Back", callback_data="back_main"))
    return builder.as_markup()


def bot_settings_kb(bot_doc: dict) -> InlineKeyboardMarkup:
    bot_id = bot_doc["bot_id"]
    anonymous = bot_doc.get("anonymous", False)
    anon_label = "Anonymous mode: On" if anonymous else "Anonymous mode: Off"
    notify_in = "On" if bot_doc.get("notify_received", False) else "Off"
    notify_reply = "On" if bot_doc.get("notify_reply_sent", False) else "Off"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Localizations", callback_data=f"locales:{bot_id}"))
    builder.row(
        InlineKeyboardButton(
            text=f"📥 “Sent to admin” notice: {notify_in}",
            callback_data=f"toggle_notify_received:{bot_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📤 “Reply sent” notice: {notify_reply}",
            callback_data=f"toggle_notify_reply:{bot_id}",
        )
    )
    builder.row(InlineKeyboardButton(text="👥 Groups", callback_data=f"groups:{bot_id}"))
    builder.row(InlineKeyboardButton(text="📢 Broadcast", callback_data=f"broadcast_info:{bot_id}"))
    builder.row(InlineKeyboardButton(text="📊 Statistics", callback_data=f"stats:{bot_id}"))
    builder.row(InlineKeyboardButton(text=f"🕶 {anon_label}", callback_data=f"toggle_anon:{bot_id}"))
    builder.row(InlineKeyboardButton(text="🔌 Disconnect Bot", callback_data=f"disconnect:{bot_id}"))
    builder.row(InlineKeyboardButton(text="« Back to Bots List", callback_data="my_bots"))
    return builder.as_markup()


def confirm_disconnect_kb(bot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, disconnect", callback_data=f"confirm_disconnect:{bot_id}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"bot:{bot_id}"),
    )
    return builder.as_markup()


def locales_kb(bot_id: int, locales: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lang in locales:
        builder.row(
            InlineKeyboardButton(text=f"🌐 {lang.upper()}", callback_data=f"locale_view:{bot_id}:{lang}")
        )
    builder.row(InlineKeyboardButton(text="« Back", callback_data=f"bot:{bot_id}"))
    return builder.as_markup()


def locale_lang_kb(bot_id: int, lang: str, bot_doc: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    default = bot_doc.get("default_locale", "en")
    if lang == default:
        builder.row(
            InlineKeyboardButton(
                text="Change the welcome text",
                callback_data=f"locale_edit:{bot_id}:{lang}:start",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="Change auto-reply texts",
            callback_data=f"locale_autoreply:{bot_id}:{lang}",
        )
    )
    builder.row(InlineKeyboardButton(text="« Back", callback_data=f"locales:{bot_id}"))
    return builder.as_markup()


def locale_autoreply_kb(bot_id: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="“Sent to admin” message",
            callback_data=f"locale_edit:{bot_id}:{lang}:received",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="“Reply sent” message",
            callback_data=f"locale_edit:{bot_id}:{lang}:reply_sent",
        )
    )
    builder.row(InlineKeyboardButton(text="« Back", callback_data=f"locale_view:{bot_id}:{lang}"))
    return builder.as_markup()
