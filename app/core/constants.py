DEFAULT_START_MESSAGE = (
    "👋 <b>Welcome!</b>\n\n"
    "Send me a message and I'll forward it to the admin. "
    "You can send text, photos, videos, voice messages, documents, and more."
)

DEFAULT_RECEIVED_MESSAGE = "✅ Your message has been sent to the admin."

DEFAULT_REPLY_SENT_MESSAGE = "✅ Reply sent."

DEFAULT_CHILD_PROMO_FOOTER = (
    '<i>This bot was made using <a href="https://t.me/ReplyDmBot">@ReplyDmBot</a></i>'
)

MASTER_WELCOME = (
    "🤖 <b>ContactBot</b> — builder of feedback bots for Telegram.\n\n"
    "Connect your own bot and let users contact you without exposing your personal account.\n\n"
    "<b>Commands:</b>\n"
    "/addbot — connect a new bot\n"
    "/mybots — manage your bots\n"
    "/pro — view plan & upgrade to Premium\n"
    "/help — help & FAQ"
)

SUPPORTED_CONTENT_TYPES = {
    "text",
    "photo",
    "video",
    "audio",
    "voice",
    "document",
    "sticker",
    "animation",
    "video_note",
    "location",
    "contact",
    "venue",
    "poll",
    "dice",
}

DEFAULT_LOCALES = {
    "en": {
        "start": DEFAULT_START_MESSAGE,
        "received": DEFAULT_RECEIVED_MESSAGE,
        "reply_sent": DEFAULT_REPLY_SENT_MESSAGE,
        "auto_reply": "",
    },
}
