import base64
import io

import qrcode
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserClient
from app.xui_client import xui_client
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def build_client_link(uc: UserClient) -> str:
    """
    Строит ссылку-конфиг для клиента.
    Для VLESS собираем стандартную vless:// ссылку.
    Для остальных протоколов (Hysteria и т.д.) формат сильно отличается —
    здесь нужно будет доработать под конкретные параметры твоего inbound'а
    (порт, obfs, sni и т.д. из настроек 3x-ui).
    """
    address = settings.public_server_address

    if uc.protocol == "vless":
        # Пример базовой ссылки для VLESS-Reality — параметры security/pbk/sid/sni
        # нужно подставить реальные из настроек твоего inbound'а в 3x-ui.
        return (
            f"vless://{uc.client_uuid}@{address}:443"
            f"?type=tcp&security=reality&flow=xtls-rprx-vision"
            f"#{uc.client_identifier}"
        )

    # Заглушка для остальных протоколов — доработать по мере добавления
    return f"# Конфиг для протокола {uc.protocol} нужно донастроить"


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    clients = db.query(UserClient).filter(UserClient.user_id == user.id).all()

    connections = []
    for uc in clients:
        traffic = {}
        try:
            traffic = xui_client.get_client_traffic(uc.client_identifier)
        except Exception:
            # Панель может быть временно недоступна — не роняем страницу целиком
            traffic = {"error": "не удалось получить статистику"}

        connections.append({
            "protocol": uc.protocol,
            "link": build_client_link(uc),
            "identifier": uc.client_identifier,
            "traffic": traffic,
        })

    plan_name = None
    expires_at = None
    if user.subscription:
        plan_name = user.subscription.plan.name if user.subscription.plan else None
        expires_at = user.subscription.expires_at

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "plan_name": plan_name,
            "expires_at": expires_at,
            "connections": connections,
        },
    )


@router.get("/dashboard/qr/{client_id}")
def client_qr(client_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    uc = db.query(UserClient).filter(
        UserClient.id == client_id, UserClient.user_id == user.id
    ).first()
    if not uc:
        return StreamingResponse(io.BytesIO(b""), media_type="image/png")

    link = build_client_link(uc)
    img = qrcode.make(link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
