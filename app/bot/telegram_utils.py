import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

logger = logging.getLogger(__name__)


def message_can_be_relayed(message: Message) -> bool:
    """True if we can resend this update (text, media, captions, documents, etc.)."""
    try:
        message.send_copy(chat_id=0)
        return True
    except TypeError:
        return False


async def copy_message_to_chat(bot: Bot, message: Message, chat_id: int) -> int:
    """
    Deliver a copy of a message to another chat.
    Uses send_copy (file_id + caption) first; falls back to copyMessage API.
    """
    try:
        sent = await bot(message.send_copy(chat_id=chat_id))
        return sent.message_id
    except TypeError:
        logger.debug("send_copy unsupported for message_id=%s", message.message_id)
    except TelegramBadRequest as e:
        logger.debug(
            "send_copy failed for message_id=%s (%s), trying copy_message",
            message.message_id,
            e,
        )

    copied = await bot.copy_message(
        chat_id=chat_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    return copied.message_id


async def safe_edit_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in (e.message or "").lower():
            raise
