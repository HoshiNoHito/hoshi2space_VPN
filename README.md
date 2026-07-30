# hoshi2space VPN site

Лёгкий сайт для VPN-сервиса: лендинг + регистрация + личный кабинет,
интегрированный с панелью 3x-ui. Спроектирован для работы на слабом
сервере (1 ядро, 1 ГБ RAM) рядом с самим VPN.

## Стек
- FastAPI + Jinja2 (без SPA-сборки — минимум ресурсов)
- SQLite (своя маленькая база, отдельно от базы 3x-ui)
- Один процесс uvicorn под systemd, за Nginx

## Установка на сервере

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx

# создаём отдельного пользователя для сайта (не root)
sudo useradd -m -s /bin/bash deploy
sudo su - deploy

git clone <твой-репозиторий> vpn-site   # или скопируй файлы вручную
cd vpn-site
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # заполни XUI_PANEL_URL, XUI_USERNAME/PASSWORD или XUI_API_TOKEN, SECRET_KEY

mkdir -p data
python seed_plans.py   # создаёт тарифы Lite/Standart/MAX — сверь inbound_ids!
```

## Проверка вручную (перед systemd)

```bash
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Открой http://127.0.0.1:8000 через SSH-туннель или curl, чтобы убедиться, что всё работает.

## Запуск как сервис

```bash
sudo cp deploy/vpnsite.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vpnsite

sudo cp deploy/nginx.conf /etc/nginx/sites-available/hoshi2space.ru
sudo ln -s /etc/nginx/sites-available/hoshi2space.ru /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d hoshi2space.ru -d www.hoshi2space.ru
```

## Что обязательно доделать перед реальным запуском

1. **Сверить пути API 3x-ui** (`app/xui_client.py`) со Swagger-докой твоей
   панели: `<URL_ПАНЕЛИ>/panel/api-docs`. Пути `login`, `addClient`,
   `getClientTraffics` могут отличаться в зависимости от версии панели.
2. **Проверить формат `settings` при добавлении клиента** для VLESS-Reality
   и Hysteria отдельно — они разные. Проще всего: открыть панель в браузере,
   вручную добавить клиента, посмотреть в DevTools → Network, какой именно
   JSON улетает на `/panel/api/inbounds/addClient`, и подогнать код под это.
3. **Достать реальные inbound_id** и подставить в `seed_plans.py`.
4. **Настроить сборку ссылки-конфига** в `build_client_link()`
   (`app/routers/dashboard.py`) — для VLESS-Reality нужны `pbk`, `sid`, `sni`
   из настроек твоего inbound'а; для Hysteria формат ссылки другой.
5. Логику выдачи/продления подписок и оплату — сейчас всё на "тариф по
   умолчанию без оплаты", это осознанно отложено по твоей просьбе.

## Экономия ресурсов, заложенная в проект
- Один воркер uvicorn (`--workers 1`) — больше не нужно на 1 ядре.
- SQLite вместо отдельного процесса СУБД.
- bcrypt с `rounds=10` вместо дефолтных 12 — компромисс скорость/безопасность.
- Никакого Docker — прямой запуск через systemd, чтобы не терять RAM на контейнеризацию.
- `MemoryMax=300M` в systemd unit — если сайт начнёт течь по памяти, он
  перезапустится сам, не утащив за собой VPN и панель.
- Никакой сборки фронтенда (Webpack/Vite/Node) — чистый Jinja2 + CSS.
