from app.core.constants import DEFAULT_LOCALES


def get_locale_start(bot_doc: dict, lang: str | None) -> str:
    locales = bot_doc.get("locales", DEFAULT_LOCALES)
    default = bot_doc.get("default_locale", "en")
    if lang and lang in locales and locales[lang].get("start"):
        return locales[lang]["start"]
    if default in locales and locales[default].get("start"):
        return locales[default]["start"]
    return DEFAULT_LOCALES["en"]["start"]


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
