import re

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]+$")
TOKEN_FIND_RE = re.compile(r"\b(\d+:[A-Za-z0-9_-]{20,})\b")

BOTFATHER_USER_ID = 93372553


def extract_bot_token(message: Message) -> str | None:
    """Token from plain paste or forwarded @BotFather message (token embedded in text)."""
    raw = (message.text or message.caption or "").strip()
    if not raw:
        return None
    if TOKEN_RE.match(raw):
        return raw
    match = TOKEN_FIND_RE.search(raw)
    return match.group(1) if match else None


def is_botfather_forward(message: Message) -> bool:
    origin = message.forward_origin
    if origin is not None:
        sender = getattr(origin, "sender_user", None)
        if sender is not None:
            if sender.id == BOTFATHER_USER_ID:
                return True
            username = (sender.username or "").lower()
            if username == "botfather":
                return True
    forward_from = message.forward_from
    if forward_from is not None:
        if forward_from.id == BOTFATHER_USER_ID:
            return True
        if (forward_from.username or "").lower() == "botfather":
            return True
    return False


async def delete_message_safe(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
