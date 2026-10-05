import logging
from datetime import datetime, timezone, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from app.database.repositories import SubscriptionRepository, OwnerRepository

logger = logging.getLogger(__name__)

PRO_STARS_PRICE = 100  # Telegram Stars
PRO_DURATION_DAYS = 30


def create_stars_payment_router() -> Router:
    router = Router()

    @router.callback_query(F.data == "buy_pro_stars")
    async def cb_buy_pro_stars(callback: CallbackQuery, bot: Bot) -> None:
        """Send a Telegram Stars invoice for Pro plan."""
        if not callback.from_user:
            return
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Pro Plan — 1 Month",
            description="Unlock Pro: up to 50 bots, no branding, priority support.",
            payload="pro_monthly_stars",
            currency="XTR",  # Telegram Stars currency code
            prices=[LabeledPrice(label="Pro Plan (1 month)", amount=PRO_STARS_PRICE)],
        )
        await callback.answer()

    @router.pre_checkout_query()
    async def pre_checkout(query: PreCheckoutQuery) -> None:
        """Always approve Stars pre-checkout."""
        await query.answer(ok=True)

    @router.message(F.successful_payment)
    async def successful_payment_handler(
        message: Message,
        subscription_repo: SubscriptionRepository,
    ) -> None:
        """Grant Pro plan for 30 days after Stars payment."""
        if not message.from_user or not message.successful_payment:
            return
        payment = message.successful_payment
        if payment.invoice_payload != "pro_monthly_stars":
            return

        owner_id = message.from_user.id
        await subscription_repo.grant_premium(
            owner_id=owner_id,
            plan_id="PREMIUM",
            days=PRO_DURATION_DAYS,
            granted_by=None,
            payment_method="stars",
            payment_charge_id=payment.telegram_payment_charge_id,
        )
        logger.info(
            "Stars payment: owner %s granted Pro for %d days (charge=%s)",
            owner_id, PRO_DURATION_DAYS, payment.telegram_payment_charge_id,
        )
        await message.answer(
            "✅ <b>Payment successful!</b>\n\n"
            "🌟 You are now on the <b>Pro plan</b> for 30 days.\n"
            "Your bots now have no branding and you can connect up to 50 bots.",
            parse_mode="HTML",
        )

    return router
