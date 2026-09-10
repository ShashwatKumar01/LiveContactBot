from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.entitlement_service import EntitlementService


def create_plan_router() -> Router:
    router = Router()

    @router.message(Command("pro"))
    async def cmd_pro(message: Message, entitlement: EntitlementService) -> None:
        if not message.from_user:
            return
        summary = await entitlement.get_plan_summary(message.from_user.id)

        plan_line = f"<b>{summary['plan_name']}</b>"
        if summary.get("expires_at"):
            plan_line += f" (expires {summary['expires_at'].strftime('%Y-%m-%d')})"

        text = (
            f"⭐ <b>Your Plan</b>\n\n"
            f"Plan: {plan_line}\n"
            f"Bots: {summary['bots_used']} / {summary['max_bots']}\n"
            f"Broadcasts today: {summary['broadcasts_used_today']}\n\n"
            "<b>Free</b>\n"
            "• Up to 5 contact bots\n"
            "• Unlimited broadcasts\n"
            "• Small @ReplyDmBot line on your bot’s /start (like Livegram)\n\n"
            "<b>Premium</b> — ₹299/month\n"
            "• Up to 50 contact bots\n"
            "• Unlimited broadcasts\n"
            "• No branding on /start\n"
            "• Priority support\n\n"
            "<i>Payment integration coming soon. "
            "Contact support to upgrade manually for now.</i>"
        )
        await message.answer(text)

    return router
