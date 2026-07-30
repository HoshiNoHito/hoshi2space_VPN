from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 — нужно для регистрации моделей перед create_all
from app.routers import public, auth, dashboard

Base.metadata.create_all(bind=engine)

app = FastAPI(title="VPN Service")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
