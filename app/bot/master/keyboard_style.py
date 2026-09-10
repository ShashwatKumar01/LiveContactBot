from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton


def styled_btn(
    text: str,
    callback_data: str,
    style: ButtonStyle | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data, style=style)
