import io

import qrcode
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import AVATAR_COLORS
from app.database import get_db
from app.deps import get_current_user
from app.models import User, Plan
from app.validators import validate_nickname
from app.xui_client import xui_client
from app.subscription_service import change_plan, cancel_plan
from app.templates_env import templates

router = APIRouter()


def get_traffic_summary(user: User) -> dict:
    """Возвращает словарь с использованным/доступным трафиком, либо пустой при ошибке/отсутствии клиента."""
    if not user.client:
        return {}
    try:
        data = xui_client.get_client_traffic(user.client.xui_email)
    except Exception:
        return {"error": "не удалось получить статистику"}

    if not data:
        return {}

    up = data.get("up", 0) or 0
    down = data.get("down", 0) or 0
    used = up + down
    total = data.get("total", 0) or 0  # 0 = безлимит в 3x-ui

    result = {"used_bytes": used, "total_bytes": total}
    if total > 0:
        result["percent"] = min(100, round(used / total * 100, 1))
    return result


def render(request: Request, name: str, user: User, extra: dict | None = None):
    ctx = {
        "request": request,
        "user": user,
        "active_page": name,
    }
    if extra:
        ctx.update(extra)
    return templates.TemplateResponse(f"dashboard/{name}.html", ctx)


@router.get("/dashboard")
def dashboard_home(request: Request, user: User = Depends(get_current_user)):
    plan_name = None
    if user.subscription and user.subscription.is_active and user.subscription.plan:
        plan_name = user.subscription.plan.name

    traffic = get_traffic_summary(user)
    return render(request, "home", user, {"plan_name": plan_name, "traffic": traffic})


@router.get("/dashboard/account")
def account_page(request: Request, user: User = Depends(get_current_user)):
    return render(request, "account", user, {"avatar_colors": AVATAR_COLORS, "saved": False, "error": None})


@router.post("/dashboard/account")
def account_update(
    request: Request,
    nickname: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    avatar_color: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nickname_lower = nickname.lower()

    if nickname_lower != user.nickname_lower:
        error = validate_nickname(nickname)
        if error:
            return render(request, "account", user, {"avatar_colors": AVATAR_COLORS, "saved": False, "error": error})
        taken = db.query(User).filter(User.nickname_lower == nickname_lower, User.id != user.id).first()
        if taken:
            return render(request, "account", user, {"avatar_colors": AVATAR_COLORS, "saved": False, "error": "Этот никнейм уже занят"})

    if email.lower() != user.email.lower():
        taken = db.query(User).filter(func.lower(User.email) == email.lower(), User.id != user.id).first()
        if taken:
            return render(request, "account", user, {"avatar_colors": AVATAR_COLORS, "saved": False, "error": "Этот email уже используется"})

    user.nickname = nickname
    user.nickname_lower = nickname_lower
    user.email = email
    user.phone = phone or None
    if avatar_color in AVATAR_COLORS:
        user.avatar_color = avatar_color
    db.commit()

    return render(request, "account", user, {"avatar_colors": AVATAR_COLORS, "saved": True, "error": None})


@router.get("/dashboard/plan")
def plan_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plans = db.query(Plan).all()
    return render(request, "plan", user, {"plans": plans, "message": None})


@router.post("/dashboard/plan/change")
def plan_change(
    request: Request,
    plan_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = db.query(Plan).all()
    new_plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not new_plan:
        return render(request, "plan", user, {"plans": plans, "message": "Тариф не найден"})

    error = change_plan(db, user, new_plan)
    message = error or f"Тариф изменён на {new_plan.name}"
    return render(request, "plan", user, {"plans": plans, "message": message})


@router.post("/dashboard/plan/cancel")
def plan_cancel(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plans = db.query(Plan).all()
    error = cancel_plan(db, user)
    message = error or "Подписка отключена. VPN-доступ приостановлен."
    return render(request, "plan", user, {"plans": plans, "message": message})


@router.get("/dashboard/keys")
def keys_page(request: Request, user: User = Depends(get_current_user)):
    if user.is_blocked:
        return render(request, "keys", user, {"links": [], "blocked": True})

    links: list[str] = []
    if user.client:
        try:
            links = xui_client.get_client_links(user.client.xui_email)
        except Exception:
            links = []
    return render(request, "keys", user, {"links": links, "blocked": False})


@router.get("/dashboard/qr")
def client_qr(index: int = 0, user: User = Depends(get_current_user)):
    if not user.client or user.is_blocked:
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


@router.get("/dashboard/stats")
def stats_page(request: Request, user: User = Depends(get_current_user)):
    traffic = get_traffic_summary(user)
    days_subscribed = 0  # TODO: считать по истории оплаченных периодов, когда появится оплата
    return render(request, "stats", user, {"traffic": traffic, "days_subscribed": days_subscribed})


@router.get("/dashboard/support")
def support_page(request: Request, user: User = Depends(get_current_user)):
    return render(request, "support", user)
