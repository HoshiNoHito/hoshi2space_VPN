"""
Разовый скрипт создания тарифов. Запусти один раз после первого старта:
    python seed_plans.py

Важно: inbound_ids ниже — ЗАГЛУШКИ. Замени на реальные ID inbound'ов
из твоей панели 3x-ui (посмотреть можно в списке Inbounds или через
xui_client.list_inbounds()).
"""
from app.database import SessionLocal, Base, engine
from app.models import Plan

Base.metadata.create_all(bind=engine)

db = SessionLocal()

plans = [
    {"name": "Lite", "price_rub": 150, "inbound_ids": [1]},
    {"name": "Standart", "price_rub": 250, "inbound_ids": [1, 4]},
    {"name": "MAX", "price_rub": 400, "inbound_ids": [1, 4},
]

for p in plans:
    existing = db.query(Plan).filter(Plan.name == p["name"]).first()
    if existing:
        existing.inbound_ids = p["inbound_ids"]
    else:
        db.add(Plan(**p))

db.commit()
db.close()
print("Тарифы созданы/обновлены.")
