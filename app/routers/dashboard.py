import io

import qrcode
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.xui_client import xui_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    links: list[str] = []
    traffic = {}

    if user.client:
        try:
            links = xui_client.get_client_links(user.client.xui_email)
        except Exception:
            links = []
        try:
            traffic = xui_client.get_client_traffic(user.client.xui_email)
        except Exception:
            traffic = {"error": "не удалось получить статистику"}

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
            "links": links,
            "traffic": traffic,
        },
    )


@router.get("/dashboard/qr")
def client_qr(index: int = 0, user: User = Depends(get_current_user)):
    """QR-код для конкретной ссылки по её индексу в списке (см. /dashboard)."""
    if not user.client:
        return StreamingResponse(io.BytesIO(b""), media_type="image/png")

    try:
        links = xui_client.get_client_links(user.client.xui_email)
        link = links[index]
    except Exception:
        return StreamingResponse(io.BytesIO(b""), media_type="image/png")

    img = qrcode.make(link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
