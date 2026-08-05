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

    checks = [
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"[0-9]", password)),
        bool(re.search(r"[^a-zA-Z0-9]", password)),
    ]
    if sum(checks) < 2:
        return "Пароль должен содержать минимум 2 из 3: заглавную букву, цифру, символ"

    return None
