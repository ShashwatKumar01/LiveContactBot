from aiogram.filters import BaseFilter
from aiogram.types import Message


class NotCommandFilter(BaseFilter):
    """Pass for media and plain text; skip messages that look like /commands."""

    async def __call__(self, message: Message) -> bool:
        text = (message.text or "").strip()
        return not text.startswith("/")
