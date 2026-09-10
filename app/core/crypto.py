from cryptography.fernet import Fernet, InvalidToken


def _get_fernet(key: str | None) -> Fernet | None:
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(token: str, key: str | None) -> str:
    fernet = _get_fernet(key)
    if not fernet:
        return token
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str, key: str | None) -> str:
    fernet = _get_fernet(key)
    if not fernet:
        return encrypted
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return encrypted
