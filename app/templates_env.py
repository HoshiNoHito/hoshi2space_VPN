from fastapi.templating import Jinja2Templates

from app.database import SessionLocal
from app.models import User

templates = Jinja2Templates(directory="app/templates")


def is_admin_request(request) -> bool:
    """Используется в base.html, чтобы показать пункт 'Админка' только админам."""
    user_id = request.session.get("user_id")
    if not user_id:
        return False
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return bool(user and user.is_admin)
    finally:
        db.close()


templates.env.globals["is_admin_request"] = is_admin_request
