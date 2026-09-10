DEFAULT_START_MESSAGE = (
    "👋 <b>Welcome!</b>\n\n"
    "Send me a message and I'll forward it to the admin. "
    "You can send text, photos, videos, voice messages, documents, and more."
)

DEFAULT_RECEIVED_MESSAGE = "✅ Your message has been sent to the admin."

DEFAULT_REPLY_SENT_MESSAGE = "✅ Reply sent."

MASTER_WELCOME = (
    "🤖 <b>ContactBot</b> — builder of feedback bots for Telegram.\n\n"
    "Connect your own bot and let users contact you without exposing your personal account.\n\n"
    "<b>Commands:</b>\n"
    "/addbot — connect a new bot\n"
    "/mybots — manage your bots\n"
    "/pro — view plan & upgrade to Premium\n"
    "/help — help & FAQ\n"
    "/lang — change language"
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
    "poll",
    "dice",
}

DEFAULT_LOCALES = {
    "en": {
        "start": DEFAULT_START_MESSAGE,
        "received": DEFAULT_RECEIVED_MESSAGE,
        "reply_sent": DEFAULT_REPLY_SENT_MESSAGE,
    },
    "hi": {
        "start": (
            "👋 <b>स्वागत है!</b>\n\n"
            "मुझे संदेश भेजें और मैं इसे एडमिन को भेज दूंगा।"
        ),
        "received": "✅ आपका संदेश एडमिन को भेज दिया गया है।",
        "reply_sent": "✅ जवाब भेज दिया गया।",
    },
}
