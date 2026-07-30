import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subscription = relationship(
        "UserSubscription", back_populates="user", uselist=False
    )
    clients = relationship("UserClient", back_populates="user")


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
    Привязка: у какого пользователя какой клиент создан в каком inbound'е 3x-ui.
    client_identifier — это email/UUID, под которым клиент создан в 3x-ui
    (используется для запроса трафика через getClientTraffics).
    """
    __tablename__ = "user_clients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    inbound_id = Column(Integer, nullable=False)
    protocol = Column(String, nullable=False)  # vless / hysteria / ...
    client_identifier = Column(String, nullable=False)  # email в 3x-ui
    client_uuid = Column(String, nullable=True)  # uuid клиента (для vless/vmess)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="clients")
