from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NewsPost, DownloadItem, FaqItem
from app.templates_env import templates

router = APIRouter()


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/news")
def news(request: Request, db: Session = Depends(get_db)):
    posts = db.query(NewsPost).order_by(NewsPost.created_at.desc()).all()
    return templates.TemplateResponse("news.html", {"request": request, "posts": posts})


@router.get("/downloads")
def downloads(request: Request, db: Session = Depends(get_db)):
    items = db.query(DownloadItem).order_by(DownloadItem.sort_order, DownloadItem.id).all()
    return templates.TemplateResponse("downloads.html", {"request": request, "items": items})


@router.get("/faq")
def faq(request: Request, db: Session = Depends(get_db)):
    items = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
    return templates.TemplateResponse("faq.html", {"request": request, "items": items})
