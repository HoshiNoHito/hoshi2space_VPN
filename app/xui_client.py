"""
Тонкая обёртка над API 3x-ui.

ВАЖНО: пути эндпоинтов ниже соответствуют стандартной структуре 3x-ui API
(login, panel/api/inbounds/*), но могут отличаться в зависимости от версии
твоей панели. Перед первым запуском в продакшене сверься со Swagger-докой
твоей панели: <URL_ПАНЕЛИ>/panel/api-docs — и поправь пути при расхождении.

Аутентификация поддерживает два режима:
- логин/пароль -> сессионная cookie (используется по умолчанию)
- Bearer API-токен, если он задан в настройках (XUI_API_TOKEN)
"""

import httpx

from app.config import settings


class XUIClient:
    def __init__(self):
        self.base_url = settings.xui_panel_url.rstrip("/")
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client

        headers = {}
        if settings.xui_api_token:
            headers["Authorization"] = f"Bearer {settings.xui_api_token}"

        # verify=False пригодится, если у панели самоподписанный сертификат
        # на внутреннем адресе — поправь на True, если сертификат валидный.
        client = httpx.Client(base_url=self.base_url, headers=headers, timeout=10.0)

        if not settings.xui_api_token:
            # логинимся по логину/паролю, cookie сохранится в client automatically
            resp = client.post(
                "/login",
                data={"username": settings.xui_username, "password": settings.xui_password},
            )
            resp.raise_for_status()

        self._client = client
        return client

    def list_inbounds(self) -> list[dict]:
        client = self._get_client()
        resp = client.get("/panel/api/inbounds/list")
        resp.raise_for_status()
        return resp.json().get("obj", [])

    def add_client(self, inbound_id: int, email: str, client_uuid: str,
                    expiry_time_ms: int = 0, total_gb: int = 0) -> dict:
        """
        Добавляет клиента в указанный inbound.
        Структура `settings` (JSON-строка) зависит от протокола inbound'а —
        для vless/vmess нужен client с id (uuid); для hysteria и других
        протоколов поля отличаются. Проверь актуальный формат через
        "Inspect -> Network" в браузере при ручном добавлении клиента в панели,
        как рекомендует официальная документация 3x-ui.
        """
        client = self._get_client()
        payload = {
            "id": inbound_id,
            "settings": {
                "clients": [
                    {
                        "id": client_uuid,
                        "email": email,
                        "enable": True,
                        "expiryTime": expiry_time_ms,
                        "totalGB": total_gb,
                    }
                ]
            },
        }
        resp = client.post("/panel/api/inbounds/addClient", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_client_traffic(self, email: str) -> dict:
        client = self._get_client()
        resp = client.get(f"/panel/api/inbounds/getClientTraffics/{email}")
        resp.raise_for_status()
        return resp.json().get("obj", {})

    def delete_client(self, inbound_id: int, client_uuid: str) -> dict:
        client = self._get_client()
        resp = client.post(f"/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}")
        resp.raise_for_status()
        return resp.json()


# Единственный инстанс на всё приложение — переиспользует TCP-соединение и cookie
xui_client = XUIClient()
