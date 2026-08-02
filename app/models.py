import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    nickname = Column(String, unique=True, index=True, nullable=False)
    nickname_lower = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    avatar_color = Column(String, default="#5b8cff")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subscription = relationship(
        "UserSubscription", back_populates="user", uselist=False
    )
    client = relationship("UserClient", back_populates="user", uselist=False)


class Plan(Base):
    """
    Тариф. inbound_ids хранит список ID inbound'ов в 3x-ui,
    которые доступны пользователю на этом тарифе.
    Например: Lite -> [1], Standart -> [1, 2], MAX -> [1, 2, 3]
    """
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # Lite / Standart / MAX
    price_rub = Column(Integer, default=0)  # цена в рублях, 0 пока без оплаты
    inbound_ids = Column(JSON, default=list)  # [1, 2, 3]
    traffic_limit_gb = Column(Integer, nullable=True)  # None = безлимит


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    expires_at = Column(DateTime, nullable=True)  # None = бессрочно (напр. на старте)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan")


class UserClient(Base):
    """
    Привязка пользователя к его клиенту в 3x-ui.
    Один клиент (email) может быть прикреплён сразу к нескольким inbound'ам
    (согласно тарифу) — панель обрабатывает это одним вызовом /clients/add,
    поэтому здесь достаточно одной строки на пользователя.
    """
    __tablename__ = "user_clients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    xui_email = Column(String, nullable=False)  # email клиента в 3x-ui
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="client")


class NewsPost(Base):
    __tablename__ = "news_posts"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    image_path = Column(String, nullable=True)  # относительный путь под /uploads
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DownloadItem(Base):
    __tablename__ = "download_items"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    file_path = Column(String, nullable=False)       # хранимое имя файла на диске
    original_filename = Column(String, nullable=False)  # имя, которое увидит пользователь при скачивании
    sort_order = Column(Integer, default=0)


class FaqItem(Base):
    __tablename__ = "faq_items"

    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    image_path = Column(String, nullable=True)  # относительный путь под /uploads
    sort_order = Column(Integer, default=0)
