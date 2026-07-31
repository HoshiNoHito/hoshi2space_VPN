from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/news")
def news(request: Request):
    return templates.TemplateResponse("news.html", {"request": request})


@router.get("/downloads")
def downloads(request: Request):
    return templates.TemplateResponse("downloads.html", {"request": request})


@router.get("/faq")
def faq(request: Request):
    return templates.TemplateResponse("faq.html", {"request": request})
