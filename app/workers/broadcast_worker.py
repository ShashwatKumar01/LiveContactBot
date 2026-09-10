import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from app.core.config import Settings
from app.core.crypto import decrypt_token
from app.database.repositories import BotRepository, BotUserRepository, BroadcastRepository, OwnerRepository
from app.bot.master.keyboards import broadcast_stop_kb
from app.services.broadcast_progress import format_progress_text
from app.bot.telegram_utils import copy_ref_to_chat
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BroadcastWorker:
    def __init__(
        self,
        settings: Settings,
        bot_repo: BotRepository,
        user_repo: BotUserRepository,
        broadcast_repo: BroadcastRepository,
        owner_repo: OwnerRepository,
    ) -> None:
        self._settings = settings
        self._bot_repo = bot_repo
        self._user_repo = user_repo
        self._broadcast_repo = broadcast_repo
        self._owner_repo = owner_repo
        self._rate_limiter = RateLimiter(settings.broadcast_rate_limit)
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("Broadcast worker started")
        while self._running:
            try:
                await self._process_jobs()
            except Exception as e:
                logger.error("Broadcast worker error: %s", e)
            await asyncio.sleep(3)

    def stop(self) -> None:
        self._running = False

    async def _process_jobs(self) -> None:
        jobs = await self._broadcast_repo.get_running_jobs()
        for job in jobs:
            await self._process_job(job)

    async def _resolve_recipients(self, job: dict) -> list[int]:
        target = job.get("target", "bot_users")
        bot_id = job["bot_id"]

        if target == "all_owners":
            owners = await self._owner_repo.get_all(skip=0, limit=1_000_000)
            return [o["telegram_id"] for o in owners]
        if target == "all_users":
            return await self._user_repo.get_distinct_owner_user_ids()

        payload = job.get("payload") or {}
        if payload.get("type") == "multi_copy":
            audience = payload.get("audience", "all")
            return await self._user_repo.get_broadcast_recipient_ids(bot_id, audience)
        users = await self._user_repo.get_all_active(bot_id)
        return [u["user_id"] for u in users]

    async def _get_bot_for_job(self, job: dict) -> Bot:
        bot_id = job["bot_id"]
        if bot_id == 0:
            return Bot(token=self._settings.master_bot_token)
        bot_doc = await self._bot_repo.get_by_id(bot_id)
        if not bot_doc:
            raise ValueError(f"Bot {bot_id} not found")
        token = decrypt_token(bot_doc["token_encrypted"], self._settings.token_encryption_key)
        return Bot(token=token)

    async def _progress_bot(self, job: dict) -> Bot:
        if job.get("progress_via_master", True):
            return Bot(token=self._settings.master_bot_token)
        return await self._get_bot_for_job(job)

    async def _update_progress(self, job: dict) -> None:
        chat_id = job.get("progress_chat_id")
        message_id = job.get("progress_message_id")
        if not chat_id or not message_id:
            return
        notifier = await self._progress_bot(job)
        try:
            status = job.get("status", "")
            markup = (
                broadcast_stop_kb(job["job_id"])
                if status in ("pending", "running")
                else None
            )
            await notifier.edit_message_text(
                format_progress_text(job),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup,
            )
        except Exception as e:
            logger.debug("Progress UI update skipped: %s", e)
        finally:
            await notifier.session.close()

    async def _process_job(self, job: dict) -> None:
        job_id = job["job_id"]
        bot_id = job["bot_id"]

        job = await self._broadcast_repo.get_job(job_id) or job
        if job.get("status") == "cancelled":
            await self._update_progress(job)
            return

        if job["status"] == "pending":
            user_ids = await self._resolve_recipients(job)
            await self._broadcast_repo.add_recipients(job_id, user_ids)
            await self._broadcast_repo.update_job(
                job_id, status="running", total=len(user_ids)
            )
            job["total"] = len(user_ids)
            job = await self._broadcast_repo.get_job(job_id) or job
            await self._update_progress(job)

        job = await self._broadcast_repo.get_job(job_id) or job
        if job.get("status") == "cancelled":
            await self._update_progress(job)
            return

        try:
            bot = await self._get_bot_for_job(job)
        except ValueError:
            await self._broadcast_repo.update_job(job_id, status="failed")
            job = await self._broadcast_repo.get_job(job_id) or job
            await self._update_progress(job)
            return

        recipients = await self._broadcast_repo.get_pending_recipients(
            job_id, self._settings.broadcast_batch_size
        )
        if not recipients:
            status = "cancelled" if job.get("status") == "cancelled" else "completed"
            await self._broadcast_repo.update_job(job_id, status=status)
            job = await self._broadcast_repo.get_job(job_id) or job
            await self._update_progress(job)
            await bot.session.close()
            return

        sent = job.get("sent", 0)
        failed = job.get("failed", 0)

        payload = job.get("payload")

        for rec in recipients:
            job = await self._broadcast_repo.get_job(job_id) or job
            if job.get("status") == "cancelled":
                break
            await self._rate_limiter.acquire()
            try:
                silent = bool(payload.get("silent")) if payload else False
                if payload and payload.get("type") == "text":
                    await bot.send_message(
                        chat_id=rec["user_id"],
                        text=payload["text"],
                        parse_mode=payload.get("parse_mode", "HTML"),
                        disable_notification=silent,
                    )
                elif payload and payload.get("type") == "multi_copy":
                    for item in payload.get("messages", []):
                        await copy_ref_to_chat(
                            bot,
                            from_chat_id=item["chat_id"],
                            message_id=item["message_id"],
                            chat_id=rec["user_id"],
                            disable_notification=silent,
                        )
                else:
                    await copy_ref_to_chat(
                        bot,
                        from_chat_id=job["source_chat_id"],
                        message_id=job["source_msg_id"],
                        chat_id=rec["user_id"],
                        disable_notification=silent,
                    )
                await self._broadcast_repo.mark_recipient(job_id, rec["user_id"], "sent")
                sent += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except TelegramForbiddenError:
                await self._broadcast_repo.mark_recipient(job_id, rec["user_id"], "failed")
                if bot_id:
                    await self._user_repo.mark_blocked(bot_id, rec["user_id"])
                failed += 1
            except Exception:
                await self._broadcast_repo.mark_recipient(job_id, rec["user_id"], "failed")
                failed += 1

        await self._broadcast_repo.update_job(job_id, sent=sent, failed=failed)
        job = await self._broadcast_repo.get_job(job_id) or job
        if job.get("status") != "cancelled":
            pending_left = await self._broadcast_repo.get_pending_recipients(job_id, limit=1)
            if not pending_left:
                await self._broadcast_repo.update_job(job_id, status="completed")
                job = await self._broadcast_repo.get_job(job_id) or job
        await self._update_progress(job)
        await bot.session.close()
