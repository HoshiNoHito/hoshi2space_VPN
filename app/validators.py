import re

NICKNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")


def validate_nickname(nickname: str) -> str | None:
    """Возвращает текст ошибки, либо None если всё ок."""
    if not NICKNAME_RE.match(nickname):
        return "Никнейм должен быть от 3 до 32 символов: латинские буквы, цифры, точка, дефис, подчёркивание"
    return None


def validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Пароль должен содержать не менее 8 символов"
    if not re.search(r"[A-Z]", password):
        return "Пароль должен содержать минимум одну заглавную букву"
    if not re.search(r"[0-9]", password):
        return "Пароль должен содержать минимум одну цифру"
    return None
