import bcrypt

# bcrypt имеет собственный лимит в 72 байта на пароль — обрезаем длинные
# пароли до этого лимита вместо падения с ошибкой (бага в UX это не создаёт,
# т.к. 72 байта — это уже очень длинный пароль на практике).
_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_MAX_BYTES]
    # rounds=10 — умеренная стоимость, чтобы не грузить единственное ядро CPU
    # при регистрации нескольких пользователей одновременно
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=10))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = password.encode("utf-8")[:_MAX_BYTES]
    return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))
