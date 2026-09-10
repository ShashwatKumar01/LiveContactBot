from app.core.constants import DEFAULT_LOCALES


def get_locale_start(bot_doc: dict, lang: str | None = None) -> str:
    locales = bot_doc.get("locales", DEFAULT_LOCALES)
    en = locales.get("en") or DEFAULT_LOCALES["en"]
    return en.get("start") or DEFAULT_LOCALES["en"]["start"]


def get_locale_string(bot_doc: dict, key: str) -> str:
    locales = bot_doc.get("locales", DEFAULT_LOCALES)
    en = locales.get("en") or DEFAULT_LOCALES["en"]
    return en.get(key) or DEFAULT_LOCALES["en"].get(key, "")


def apply_user_template_vars(text: str, user) -> str:
    if not user:
        return text
    return (
        text.replace("${firstName}", user.first_name or "")
        .replace("${lastName}", user.last_name or "")
        .replace("${username}", user.username or "")
    )


def append_promo_footer(start_text: str, footer: str) -> str:
    footer = (footer or "").strip()
    if not footer:
        return start_text
    return f"{start_text.rstrip()}\n\n{footer}"
