from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Plan, UserSubscription, UserClient
from app.security import hash_password, verify_password
from app.xui_client import xui_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_PLAN_NAME = "Lite"  # тариф по умолчанию при регистрации (пока без оплаты)


@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пользователь с таким email уже существует"},
        )

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # Назначаем дефолтный тариф, если он существует в базе
    default_plan = db.query(Plan).filter(Plan.name == DEFAULT_PLAN_NAME).first()
    if default_plan:
        sub = UserSubscription(user_id=user.id, plan_id=default_plan.id, is_active=True)
        db.add(sub)
        db.commit()

        # Создаём клиента в 3x-ui сразу по всем inbound'ам тарифа одним вызовом
        try:
            xui_client.add_client(email=user.email, inbound_ids=default_plan.inbound_ids)
            db.add(UserClient(user_id=user.id, xui_email=user.email))
            db.commit()
        except Exception:
            # Панель может быть временно недоступна — не роняем регистрацию.
            # Пользователь попадёт в кабинет без подключений, это будет видно
            # и можно будет донастроить вручную/повторить позже.
            pass

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный email или пароль"},
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
