from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NewsPost, DownloadItem, FaqItem
from app.templates_env import templates
from app.uploads import DOWNLOAD_DIR

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


@router.get("/downloads/file/{item_id}")
def download_file(item_id: int, db: Session = Depends(get_db)):
    item = db.query(DownloadItem).filter(DownloadItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Файл не найден")

    path = DOWNLOAD_DIR / item.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    return FileResponse(path, filename=item.original_filename, media_type="application/octet-stream")


@router.get("/faq")
def faq(request: Request, db: Session = Depends(get_db)):
    items = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
    return templates.TemplateResponse("faq.html", {"request": request, "items": items})
