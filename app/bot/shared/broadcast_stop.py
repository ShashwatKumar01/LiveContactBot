from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.bot.master.keyboards import broadcast_stop_kb
from app.bot.telegram_utils import safe_edit_text
from app.database.repositories import BroadcastRepository
from app.services.broadcast_progress import format_progress_text


def create_broadcast_stop_router() -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("bc_stop:"))
    async def bc_stop(
        callback: CallbackQuery,
        broadcast_repo: BroadcastRepository,
    ) -> None:
        if not callback.from_user or not callback.data:
            return
        job_id = callback.data.split(":", 1)[1]
        job = await broadcast_repo.get_job(job_id)
        if not job or job.get("owner_id") != callback.from_user.id:
            await callback.answer("Not found.", show_alert=True)
            return
        if job.get("status") in ("completed", "cancelled", "failed"):
            await callback.answer("Already finished.")
            return
        ok = await broadcast_repo.cancel_job(job_id, owner_id=callback.from_user.id)
        if not ok:
            await callback.answer("Could not stop.", show_alert=True)
            return
        job = await broadcast_repo.get_job(job_id) or job
        job["status"] = "cancelled"
        await safe_edit_text(
            callback.message,
            format_progress_text(job),
            reply_markup=broadcast_stop_kb(job_id),
        )
        await callback.answer("Broadcast stopped.")

    return router
