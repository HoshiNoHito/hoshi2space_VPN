from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models import User, NewsPost, DownloadItem, FaqItem
from app.templates_env import templates

router = APIRouter(prefix="/admin")


@router.get("")
def admin_home(request: Request, admin: User = Depends(get_current_admin)):
    return templates.TemplateResponse("admin/home.html", {"request": request, "active": "home"})


# --- Новости ---

@router.get("/news")
def news_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    posts = db.query(NewsPost).order_by(NewsPost.created_at.desc()).all()
    return templates.TemplateResponse("admin/news.html", {"request": request, "active": "news", "posts": posts})


@router.post("/news/create")
def news_create(
    title: str = Form(...),
    content: str = Form(...),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    db.add(NewsPost(title=title, content=content))
    db.commit()
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/news/{post_id}/update")
def news_update(
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if post:
        post.title = title
        post.content = content
        db.commit()
    return RedirectResponse(url="/admin/news", status_code=303)


@router.post("/news/{post_id}/delete")
def news_delete(post_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse(url="/admin/news", status_code=303)


# --- Скачать ---

@router.get("/downloads")
def downloads_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    items = db.query(DownloadItem).order_by(DownloadItem.sort_order, DownloadItem.id).all()
    return templates.TemplateResponse("admin/downloads.html", {"request": request, "active": "downloads", "items": items})


@router.post("/downloads/create")
def downloads_create(
    title: str = Form(...),
    description: str = Form(...),
    download_url: str = Form(...),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    db.add(DownloadItem(title=title, description=description, download_url=download_url, sort_order=sort_order))
    db.commit()
    return RedirectResponse(url="/admin/downloads", status_code=303)


@router.post("/downloads/{item_id}/update")
def downloads_update(
    item_id: int,
    title: str = Form(...),
    description: str = Form(...),
    download_url: str = Form(...),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadItem).filter(DownloadItem.id == item_id).first()
    if item:
        item.title = title
        item.description = description
        item.download_url = download_url
        item.sort_order = sort_order
        db.commit()
    return RedirectResponse(url="/admin/downloads", status_code=303)


@router.post("/downloads/{item_id}/delete")
def downloads_delete(item_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(DownloadItem).filter(DownloadItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/downloads", status_code=303)


# --- FAQ ---

@router.get("/faq")
def faq_list(request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    items = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
    return templates.TemplateResponse("admin/faq.html", {"request": request, "active": "faq", "items": items})


@router.post("/faq/create")
def faq_create(
    question: str = Form(...),
    answer: str = Form(...),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    db.add(FaqItem(question=question, answer=answer, sort_order=sort_order))
    db.commit()
    return RedirectResponse(url="/admin/faq", status_code=303)


@router.post("/faq/{item_id}/update")
def faq_update(
    item_id: int,
    question: str = Form(...),
    answer: str = Form(...),
    sort_order: int = Form(0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if item:
        item.question = question
        item.answer = answer
        item.sort_order = sort_order
        db.commit()
    return RedirectResponse(url="/admin/faq", status_code=303)


@router.post("/faq/{item_id}/delete")
def faq_delete(item_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/faq", status_code=303)
