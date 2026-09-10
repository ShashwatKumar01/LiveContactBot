from aiogram.types import InlineKeyboardButton


def styled_btn(text: str, callback_data: str, style=None) -> InlineKeyboardButton:
    """Inline button (style ignored on aiogram < 3.14; safe on all versions)."""
    return InlineKeyboardButton(text=text, callback_data=callback_data)
