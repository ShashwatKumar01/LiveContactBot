import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import Message

from app.bot.telegram_utils import copy_message_to_chat, message_can_be_relayed
from app.services.child_start_text import apply_user_template_vars
from app.database.repositories import BotRepository, BotUserRepository, MessageMapRepository
from app.services.owner_alert_service import OwnerAlertService

logger = logging.getLogger(__name__)


class RelayService:
    def __init__(
        self,
        bot_repo: BotRepository,
        user_repo: BotUserRepository,
        msg_map_repo: MessageMapRepository,
    ) -> None:
        self._bot_repo = bot_repo
        self._user_repo = user_repo
        self._msg_map_repo = msg_map_repo
        self._owner_alerts: OwnerAlertService | None = None
        self._master_bot: Bot | None = None

    def set_owner_notifier(
        self, owner_alerts: OwnerAlertService, master_bot: Bot
    ) -> None:
        self._owner_alerts = owner_alerts
        self._master_bot = master_bot

    async def _notify_delivery_failed(self, bot_doc: dict) -> None:
        if not self._owner_alerts or not self._master_bot:
            return
        await self._owner_alerts.notify_once(
            self._master_bot,
            bot_doc["owner_id"],
            bot_doc["bot_id"],
            bot_doc.get("username") or "bot",
            "delivery_failed",
            "Users are messaging your bot but delivery to you failed. "
            "Open your bot and send /start, or add the bot to your group with permission to post.",
        )

    def _get_locale_string(self, bot_doc: dict, key: str, lang: str | None) -> str:
        locales = bot_doc.get("locales", {})
        default = bot_doc.get("default_locale", "en")
        if lang and lang in locales and key in locales[lang]:
            return locales[lang][key]
        if default in locales and key in locales[default]:
            return locales[default][key]
        from app.core.constants import DEFAULT_LOCALES
        return DEFAULT_LOCALES["en"].get(key, "")

    def _user_header(self, message: Message) -> str | None:
        user = message.from_user
        if not user:
            return None
        parts = []
        if user.first_name:
            parts.append(user.first_name)
        if user.last_name:
            parts.append(user.last_name)
        name = " ".join(parts) or "User"
        username = f"@{user.username}" if user.username else f"ID: {user.id}"
        return f"📩 <b>{name}</b> ({username})"

    def _admin_destination(self, bot_doc: dict) -> int:
        group_id = bot_doc.get("group_id")
        if group_id:
            return group_id
        return bot_doc["owner_id"]

    async def relay_user_to_admin(
        self, bot: Bot, bot_doc: dict, message: Message
    ) -> bool:
        bot_id = bot_doc["bot_id"]
        user = message.from_user
        if not user:
            return False

        user_doc, is_new = await self._user_repo.upsert(
            bot_id=bot_id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            language_code=user.language_code,
        )
        if is_new:
            await self._bot_repo.increment_stat(bot_id, "total_users")

        dest = self._admin_destination(bot_doc)
        header = self._user_header(message)
        if header:
            try:
                header_msg = await bot.send_message(dest, header)
                await self._msg_map_repo.create(
                    bot_id=bot_id,
                    user_id=user.id,
                    user_msg_id=message.message_id,
                    admin_chat_id=dest,
                    admin_msg_id=header_msg.message_id,
                    direction="header",
                )
            except TelegramForbiddenError:
                logger.warning("Cannot send to admin chat %s for bot %s", dest, bot_id)
                await self._notify_delivery_failed(bot_doc)
                return False

        try:
            # file_id / copyMessage only — no getFile or download on our host
            admin_msg_id = await copy_message_to_chat(bot, message, dest)
        except TelegramBadRequest as e:
            logger.error("Failed to copy message for bot %s: %s", bot_id, e)
            return False
        except TelegramForbiddenError:
            logger.warning("Forbidden copying to admin chat %s", dest)
            await self._notify_delivery_failed(bot_doc)
            return False

        await self._msg_map_repo.create(
            bot_id=bot_id,
            user_id=user.id,
            user_msg_id=message.message_id,
            admin_chat_id=dest,
            admin_msg_id=admin_msg_id,
            direction="user_to_admin",
        )
        await self._bot_repo.increment_stat(bot_id, "incoming_messages")

        if not bot_doc.get("notify_received", False):
            return True

        received_text = self._get_locale_string(
            bot_doc, "received", user.language_code
        )
        if received_text:
            received_text = apply_user_template_vars(received_text, user)
            try:
                await message.answer(received_text)
            except TelegramForbiddenError:
                await self._user_repo.mark_blocked(bot_id, user.id)

        return True

    async def relay_admin_to_user(
        self, bot: Bot, bot_doc: dict, message: Message
    ) -> bool:
        if not message.reply_to_message:
            return False

        bot_id = bot_doc["bot_id"]
        reply_id = message.reply_to_message.message_id
        mapping = await self._msg_map_repo.find_by_admin_msg(
            bot_id, message.chat.id, reply_id
        )
        if not mapping:
            mapping = await self._msg_map_repo.find_by_admin_msg_id(bot_id, reply_id)
        if not mapping:
            return False

        user_id = mapping["user_id"]
        try:
            user_msg_id = await copy_message_to_chat(bot, message, user_id)
        except TelegramForbiddenError:
            await self._user_repo.mark_blocked(bot_id, user_id)
            return False
        except TelegramBadRequest as e:
            logger.error("Failed to relay reply for bot %s: %s", bot_id, e)
            return False

        await self._msg_map_repo.create(
            bot_id=bot_id,
            user_id=user_id,
            user_msg_id=user_msg_id,
            admin_chat_id=message.chat.id,
            admin_msg_id=message.message_id,
            direction="admin_to_user",
        )
        await self._bot_repo.increment_stat(bot_id, "outgoing_messages")
        return True

    def is_supported_message(self, message: Message) -> bool:
        return message_can_be_relayed(message)

    def is_admin_message(self, bot_doc: dict, user_id: int, chat_id: int) -> bool:
        owner_id = bot_doc["owner_id"]
        group_id = bot_doc.get("group_id")
        if chat_id == owner_id and user_id == owner_id:
            return True
        if group_id and chat_id == group_id:
            return True
        return False
