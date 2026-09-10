from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def superadmin_main_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 System Stats", callback_data="sa:stats"))
    builder.row(InlineKeyboardButton(text="🤖 All Bots", callback_data="sa:bots:0"))
    builder.row(InlineKeyboardButton(text="👥 All Owners", callback_data="sa:owners:0"))
    builder.row(InlineKeyboardButton(text="⭐ Premium Plans", callback_data="sa:premium"))
    builder.row(InlineKeyboardButton(text="📢 Master Broadcast", callback_data="sa:broadcast"))
    builder.row(InlineKeyboardButton(text="🔄 Restart All Bots", callback_data="sa:restart"))
    builder.row(InlineKeyboardButton(text="🗄 DB Check", callback_data="sa:dbcheck"))
    return builder.as_markup()


def superadmin_bots_kb(bots: list[dict], page: int, has_more: bool) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for b in bots:
        status = b.get("status", "?")
        icon = "🟢" if status == "active" else "🔴"
        username = b.get("username", "unknown")
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} @{username} (owner {b.get('owner_id')})",
                callback_data=f"sa:bot:{b['bot_id']}",
            )
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« Prev", callback_data=f"sa:bots:{page - 1}"))
    if has_more:
        nav.append(InlineKeyboardButton(text="Next »", callback_data=f"sa:bots:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="« Admin Panel", callback_data="sa:main"))
    return builder.as_markup()


def superadmin_bot_detail_kb(bot_id: int, status: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if status == "active":
        builder.row(InlineKeyboardButton(text="⛔ Disable Bot", callback_data=f"sa:disable:{bot_id}"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Enable Bot", callback_data=f"sa:enable:{bot_id}"))
    builder.row(InlineKeyboardButton(text="« Back", callback_data="sa:bots:0"))
    return builder.as_markup()


def superadmin_owners_kb(owners: list[dict], page: int, has_more: bool) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for o in owners:
        tid = o.get("telegram_id")
        name = o.get("username") or o.get("first_name") or str(tid)
        banned = "🚫" if o.get("banned") else "👤"
        builder.row(
            InlineKeyboardButton(text=f"{banned} {name} ({tid})", callback_data=f"sa:owner:{tid}")
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« Prev", callback_data=f"sa:owners:{page - 1}"))
    if has_more:
        nav.append(InlineKeyboardButton(text="Next »", callback_data=f"sa:owners:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="« Admin Panel", callback_data="sa:main"))
    return builder.as_markup()


def superadmin_owner_detail_kb(owner_id: int, banned: bool, is_premium: bool = False) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if is_premium:
        builder.row(InlineKeyboardButton(text="⬇️ Revoke Premium", callback_data=f"sa:revoke_premium:{owner_id}"))
    else:
        builder.row(InlineKeyboardButton(text="⭐ Grant Premium", callback_data=f"sa:grant_premium:{owner_id}"))
    if banned:
        builder.row(InlineKeyboardButton(text="✅ Unban Owner", callback_data=f"sa:unban:{owner_id}"))
    else:
        builder.row(InlineKeyboardButton(text="🚫 Ban Owner", callback_data=f"sa:ban:{owner_id}"))
    builder.row(InlineKeyboardButton(text="« Back", callback_data="sa:owners:0"))
    return builder.as_markup()


def broadcast_confirm_kb(target: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"sa:bc_confirm:{target}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="sa:bc_cancel"),
    )
    return builder.as_markup()
