from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models import User, NewsPost, DownloadItem, FaqItem, Plan
from app.templates_env import templates
from app.uploads import save_image, save_download_file, delete_upload_quiet, delete_file_quiet, UploadTooLarge
from app.subscription_service import change_plan
from app.xui_client import xui_client

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
        group_by_email = {}

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
        "is_root": admin.is_root_admin,
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


@router.post("/users/{user_id}/toggle-admin")
def user_toggle_admin(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if not admin.is_root_admin:
        raise HTTPException(status_code=403, detail="Только главный администратор может назначать админов")

    u = db.query(User).filter(User.id == user_id).first()
    if u and not u.is_root_admin:
        u.is_admin = not u.is_admin
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
