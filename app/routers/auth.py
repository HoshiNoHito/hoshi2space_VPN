from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.database import get_db
from app.models import User, Plan, UserSubscription, UserClient
from app.security import hash_password, verify_password
from app.validators import validate_nickname, validate_password
from app.xui_client import xui_client
from app.templates_env import templates

router = APIRouter()

DEFAULT_PLAN_NAME = "Lite"  # тариф по умолчанию при регистрации (пока без оплаты)


@router.get("/check-nickname")
def check_nickname(value: str, db: Session = Depends(get_db)):
    error = validate_nickname(value)
    if error:
        return JSONResponse({"available": False, "message": error})

    exists = db.query(User).filter(User.nickname_lower == value.lower()).first()
    if exists:
        return JSONResponse({"available": False, "message": "Этот никнейм уже занят"})

    return JSONResponse({"available": True, "message": "Никнейм свободен"})


@router.get("/check-email")
def check_email(value: str, db: Session = Depends(get_db)):
    exists = db.query(User).filter(func.lower(User.email) == value.lower()).first()
    if exists:
        return JSONResponse({"available": False, "message": "Этот email уже зарегистрирован"})

    return JSONResponse({"available": True, "message": "Email свободен"})


@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": None, "nickname": "", "email": ""}
    )


@router.post("/register")
def register(
    request: Request,
    nickname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    def error_page(message: str):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": message, "nickname": nickname, "email": email},
        )

    nickname_error = validate_nickname(nickname)
    if nickname_error:
        return error_page(nickname_error)

    password_error = validate_password(password)
    if password_error:
        return error_page(password_error)

    if password != password_confirm:
        return error_page("Пароли не совпадают")

    nickname_lower = nickname.lower()

    if db.query(User).filter(User.nickname_lower == nickname_lower).first():
        return error_page("Этот никнейм уже занят")

    if db.query(User).filter(User.email == email).first():
        return error_page("Пользователь с таким email уже существует")

    user = User(
        nickname=nickname,
        nickname_lower=nickname_lower,
        email=email,
        password_hash=hash_password(password),
    )
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
            pass

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "identifier": ""})


@router.post("/login")
def login(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    identifier_lower = identifier.strip().lower()

    user = (
        db.query(User)
        .filter((func.lower(User.email) == identifier_lower) | (User.nickname_lower == identifier_lower))
        .first()
    )

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверные данные для входа", "identifier": identifier},
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
