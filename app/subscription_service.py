"""
Общая логика смены/отмены тарифа — используется и в личном кабинете
пользователя (app/routers/dashboard.py), и в админке (app/routers/admin.py),
чтобы не дублировать вызовы к 3x-ui в двух местах.
"""

from sqlalchemy.orm import Session

from app.models import User, Plan, UserSubscription, UserClient
from app.xui_client import xui_client


def change_plan(db: Session, user: User, new_plan: Plan) -> str | None:
    """Меняет тариф пользователя. Возвращает текст ошибки, либо None при успехе."""
    old_ids = set()
    if user.subscription and user.subscription.plan:
        old_ids = set(user.subscription.plan.inbound_ids or [])
    new_ids = set(new_plan.inbound_ids or [])

    to_attach = list(new_ids - old_ids)
    to_detach = list(old_ids - new_ids)

    if not user.client:
        try:
            xui_client.add_client(email=user.email, inbound_ids=list(new_ids))
            db.add(UserClient(user_id=user.id, xui_email=user.email))
        except Exception:
            return "Не удалось подключиться к панели VPN, попробуйте позже"
    else:
        try:
            if to_attach:
                xui_client.attach_inbounds(user.client.xui_email, to_attach)
            if to_detach:
                xui_client.detach_inbounds(user.client.xui_email, to_detach)
        except Exception:
            return "Не удалось обновить подключения в панели VPN, попробуйте позже"

    if user.subscription:
        user.subscription.plan_id = new_plan.id
        user.subscription.is_active = True
    else:
        db.add(UserSubscription(user_id=user.id, plan_id=new_plan.id, is_active=True))

    db.commit()
    return None


def cancel_plan(db: Session, user: User) -> str | None:
    """Отключает подписку (снимает VPN-доступ). Возвращает текст ошибки, либо None при успехе."""
    if user.subscription and user.subscription.plan and user.client:
        old_ids = list(user.subscription.plan.inbound_ids or [])
        try:
            xui_client.detach_inbounds(user.client.xui_email, old_ids)
        except Exception:
            return "Не удалось отключить VPN-доступ в панели, попробуйте позже"

    if user.subscription:
        user.subscription.is_active = False
        db.commit()

    return None
