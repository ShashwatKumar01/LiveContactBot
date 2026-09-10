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

    Does not download media to this server — only Telegram API calls with
    file_id (send_photo/send_document/…) or copyMessage by chat+message id.
    Large files stay on Telegram; Railway bandwidth is not used for file bytes.
    """
    try:
        return await copy_ref_to_chat(
            bot,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            chat_id=chat_id,
        )
    except TelegramBadRequest as e:
        logger.warning(
            "copy_message failed for message_id=%s (%s), trying send_copy",
            message.message_id,
            e,
        )

    try:
        sent = await bot(message.send_copy(chat_id=chat_id))
        return sent.message_id
    except TypeError:
        logger.error("send_copy unsupported for message_id=%s", message.message_id)
        raise


async def copy_ref_to_chat(
    bot: Bot,
    *,
    from_chat_id: int,
    message_id: int,
    chat_id: int,
    disable_notification: bool | None = None,
) -> int:
    """copyMessage by reference only (no file download on this server)."""
    copied = await bot.copy_message(
        chat_id=chat_id,
        from_chat_id=from_chat_id,
        message_id=message_id,
        disable_notification=disable_notification,
    )
    return copied.message_id


async def safe_edit_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in (e.message or "").lower():
            raise
