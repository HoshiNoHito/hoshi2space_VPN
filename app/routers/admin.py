from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models import User, NewsPost, DownloadItem, FaqItem, Plan
from app.templates_env import templates
from app.uploads import save_image, save_download_file, delete_upload_quiet, delete_file_quiet, UploadTooLarge
from app.subscription_service import change_plan
from app.xui_client import xui_client
from app.security import hash_password
from app.validators import validate_nickname
from app.models import UserClient, UserSubscription

router = APIRouter(prefix="/admin")


@router.get("")
def admin_home(request: Request, admin: User = Depends(get_current_admin)):
    return templates.TemplateResponse("admin/home.html", {"request": request, "active": "home"})


# --- Новости ---

@router.get("/news")
def news_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db), error: str = None):
    posts = db.query(NewsPost).order_by(NewsPost.created_at.desc()).all()
    return templates.TemplateResponse("admin/news.html", {"request": request, "active": "news", "posts": posts, "error": error})


@router.post("/news/create")
def news_create(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        image_path = save_image(image)
    except UploadTooLarge as e:
        posts = db.query(NewsPost).order_by(NewsPost.created_at.desc()).all()
        return templates.TemplateResponse("admin/news.html", {"request": request, "active": "news", "posts": posts, "error": str(e)})

    db.add(NewsPost(title=title, content=content, image_path=image_path))
    db.commit()
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/news/{post_id}/update")
def news_update(
    request: Request,
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None),
    remove_image: str = Form(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if post:
        post.title = title
        post.content = content

        if remove_image and post.image_path:
            delete_upload_quiet(post.image_path)
            post.image_path = None

        if image and image.filename:
            new_path = save_image(image)
            if post.image_path:
                delete_upload_quiet(post.image_path)
            post.image_path = new_path

        db.commit()
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/news/{post_id}/delete")
def news_delete(post_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if post:
        if post.image_path:
            delete_upload_quiet(post.image_path)
        db.delete(post)
        db.commit()
    return RedirectResponse(url="/admin/news", status_code=303)


# --- Скачать ---

@router.get("/downloads")
def downloads_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db), error: str = None):
    items = db.query(DownloadItem).order_by(DownloadItem.sort_order, DownloadItem.id).all()
    return templates.TemplateResponse("admin/downloads.html", {"request": request, "active": "downloads", "items": items, "error": error})


@router.post("/downloads/create")
def downloads_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        stored_name, original_name = save_download_file(file)
    except UploadTooLarge as e:
        items = db.query(DownloadItem).order_by(DownloadItem.sort_order, DownloadItem.id).all()
        return templates.TemplateResponse("admin/downloads.html", {"request": request, "active": "downloads", "items": items, "error": str(e)})

    db.add(DownloadItem(
        title=title, description=description,
        file_path=stored_name, original_filename=original_name,
        sort_order=sort_order,
    ))
    db.commit()
    return RedirectResponse(url="/admin/downloads", status_code=303)


@router.post("/downloads/{item_id}/update")
def downloads_update(
    request: Request,
    item_id: int,
    title: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(None),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadItem).filter(DownloadItem.id == item_id).first()
    if item:
        item.title = title
        item.description = description
        item.sort_order = sort_order

        if file and file.filename:
            try:
                stored_name, original_name = save_download_file(file)
            except UploadTooLarge as e:
                items = db.query(DownloadItem).order_by(DownloadItem.sort_order, DownloadItem.id).all()
                return templates.TemplateResponse("admin/downloads.html", {"request": request, "active": "downloads", "items": items, "error": str(e)})
            delete_file_quiet(item.file_path)
            item.file_path = stored_name
            item.original_filename = original_name

        db.commit()
    return RedirectResponse(url="/admin/downloads", status_code=303)


@router.post("/downloads/{item_id}/delete")
def downloads_delete(item_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(DownloadItem).filter(DownloadItem.id == item_id).first()
    if item:
        delete_file_quiet(item.file_path)
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/downloads", status_code=303)


# --- FAQ ---

@router.get("/faq")
def faq_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db), error: str = None):
    items = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
    return templates.TemplateResponse("admin/faq.html", {"request": request, "active": "faq", "items": items, "error": error})


@router.post("/faq/create")
def faq_create(
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    image: UploadFile = File(None),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        image_path = save_image(image)
    except UploadTooLarge as e:
        items = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
        return templates.TemplateResponse("admin/faq.html", {"request": request, "active": "faq", "items": items, "error": str(e)})

    db.add(FaqItem(question=question, answer=answer, image_path=image_path, sort_order=sort_order))
    db.commit()
    return RedirectResponse(url="/admin/faq", status_code=303)


@router.post("/faq/{item_id}/update")
def faq_update(
    request: Request,
    item_id: int,
    question: str = Form(...),
    answer: str = Form(...),
    image: UploadFile = File(None),
    remove_image: str = Form(None),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if item:
        item.question = question
        item.answer = answer
        item.sort_order = sort_order

        if remove_image and item.image_path:
            delete_upload_quiet(item.image_path)
            item.image_path = None

        if image and image.filename:
            new_path = save_image(image)
            if item.image_path:
                delete_upload_quiet(item.image_path)
            item.image_path = new_path

        db.commit()
    return RedirectResponse(url="/admin/faq", status_code=303)


@router.post("/faq/{item_id}/delete")
def faq_delete(item_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if item:
        if item.image_path:
            delete_upload_quiet(item.image_path)
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/faq", status_code=303)


# --- Пользователи ---

@router.get("/users")
def users_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at).all()
    plans = db.query(Plan).all()

    try:
        online_emails = xui_client.get_online_emails()
    except Exception:
        online_emails = set()

    try:
        all_clients = xui_client.list_all_clients()
        # ВАЖНО: имя поля группы в ответе панели не удалось проверить вживую —
        # пробуем оба варианта названия, встречающихся в разных версиях 3x-ui.
        group_by_email = {c.get("email"): (c.get("group") or c.get("group_name") or "") for c in all_clients}
    except Exception:
        all_clients = []
        group_by_email = {}

    linked_emails = {uc.xui_email for uc in db.query(UserClient).all()}
    unlinked_emails = [c.get("email") for c in all_clients if c.get("email") and c.get("email") not in linked_emails]

    rows = []
    for u in users:
        xui_email = u.client.xui_email if u.client else None
        rows.append({
            "user": u,
            "online": bool(xui_email and xui_email in online_emails),
            "group": group_by_email.get(xui_email, "") if xui_email else "",
        })

    return templates.TemplateResponse("admin/users.html", {
        "request": request, "active": "users", "rows": rows, "plans": plans,
        "is_root": admin.is_root_admin, "unlinked_emails": unlinked_emails,
    })


@router.post("/users/{user_id}/block")
def user_block(
    user_id: int,
    reason: str = Form(""),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.is_blocked = True
        u.block_reason = reason or None
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/unblock")
def user_unblock(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.is_blocked = False
        u.block_reason = None
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/set-plan")
def user_set_plan(
    user_id: int,
    plan_id: int = Form(...),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if u and plan:
        change_plan(db, u, plan)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/link-xui")
def user_link_xui(
    user_id: int,
    xui_email: str = Form(""),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return RedirectResponse(url="/admin/users", status_code=303)

    if not xui_email:
        if u.client:
            db.delete(u.client)
            db.commit()
        return RedirectResponse(url="/admin/users", status_code=303)

    taken = db.query(UserClient).filter(UserClient.xui_email == xui_email, UserClient.user_id != user_id).first()
    if taken:
        # Уже привязан к другому аккаунту — молча игнорируем, чтобы не плодить дубли привязки
        return RedirectResponse(url="/admin/users", status_code=303)

    if u.client:
        u.client.xui_email = xui_email
    else:
        db.add(UserClient(user_id=u.id, xui_email=xui_email))
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-admin")
def user_toggle_admin(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if not admin.is_root_admin:
        raise HTTPException(status_code=403, detail="Только главный администратор может назначать админов")

    u = db.query(User).filter(User.id == user_id).first()
    if u and not u.is_root_admin:
        u.is_admin = not u.is_admin
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


# --- Импорт пользователей из 3x-ui (клиенты, добавленные вручную в панели) ---

@router.get("/users/import")
def users_import_page(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    linked_emails = {uc.xui_email for uc in db.query(UserClient).all()}

    try:
        all_clients = xui_client.list_all_clients()
    except Exception:
        all_clients = []
        error = "Не удалось получить список клиентов из панели 3x-ui"
    else:
        error = None

    candidates = [c for c in all_clients if c.get("email") and c.get("email") not in linked_emails]
    plans = db.query(Plan).all()

    return templates.TemplateResponse("admin/users_import.html", {
        "request": request, "active": "users", "candidates": candidates, "plans": plans, "error": error,
    })


@router.post("/users/import")
def users_import_create(
    request: Request,
    xui_email: str = Form(...),
    nickname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    plan_id: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    def error_page(message: str):
        linked_emails = {uc.xui_email for uc in db.query(UserClient).all()}
        try:
            all_clients = xui_client.list_all_clients()
        except Exception:
            all_clients = []
        candidates = [c for c in all_clients if c.get("email") and c.get("email") not in linked_emails]
        plans = db.query(Plan).all()
        return templates.TemplateResponse("admin/users_import.html", {
            "request": request, "active": "users", "candidates": candidates, "plans": plans, "error": message,
        })

    nickname_lower = nickname.lower()

    nick_error = validate_nickname(nickname)
    if nick_error:
        return error_page(nick_error)

    if db.query(User).filter(User.nickname_lower == nickname_lower).first():
        return error_page("Этот никнейм уже занят")

    if db.query(User).filter(func.lower(User.email) == email.lower()).first():
        return error_page("Этот email уже используется")

    if db.query(UserClient).filter(UserClient.xui_email == xui_email).first():
        return error_page("Этот клиент 3x-ui уже привязан к другому аккаунту")

    user = User(
        nickname=nickname,
        nickname_lower=nickname_lower,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Привязка без вызова 3x-ui — клиент уже существует в панели со своими inbound'ами как есть
    db.add(UserClient(user_id=user.id, xui_email=xui_email))

    if plan_id:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if plan:
            # Только учётная запись подписки для сайта — inbound'ы клиента не трогаем,
            # они уже настроены вручную в панели так, как есть
            db.add(UserSubscription(user_id=user.id, plan_id=plan.id, is_active=True))

    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
