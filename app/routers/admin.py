from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models import User, NewsPost, DownloadItem, FaqItem
from app.templates_env import templates
from app.uploads import save_image, save_download_file, delete_upload_quiet, delete_file_quiet, UploadTooLarge

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
