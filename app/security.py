from passlib.context import CryptContext

# bcrypt с умеренной стоимостью (rounds), чтобы не грузить единственное ядро CPU
# при регистрации нескольких пользователей одновременно.
# 10 — компромисс: заметно быстрее дефолтных 12, но всё ещё безопасно.
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=10)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
