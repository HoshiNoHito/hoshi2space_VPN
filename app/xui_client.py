"""
Обёртка над API 3x-ui — под реальную версию панели пользователя.

Аутентификация: Bearer API-токен (XUI_API_TOKEN в .env) — согласно
документации панели, это отключает необходимость в CSRF-токене,
который нужен только для cookie-based сессий браузера.

Базовый URL панели ДОЛЖЕН включать секретный путь-префикс, например:
    XUI_PANEL_URL=https://admin.hoshi2space.ru:33029/wSFpgdeB06LWJIXhVr/
"""

import httpx

from app.config import settings


class XUIClient:
    def __init__(self):
        # Обязательно с "/" на конце — чтобы относительные пути ниже
        # (без ведущего "/") корректно приклеивались после префикса панели
        base = settings.xui_panel_url
        self.base_url = base if base.endswith("/") else base + "/"
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client

        headers = {"Authorization": f"Bearer {settings.xui_api_token}"}
        self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=10.0)
        return self._client

    def add_client(
        self,
        email: str,
        inbound_ids: list[int],
        expiry_time_ms: int = 0,
        total_gb: int = 0,
        limit_ip: int = 0,
    ) -> dict:
        """
        Создаёт клиента и привязывает его сразу ко всем inbound_ids
        (по документации — так и задумано, один вызов на весь тариф).
        UUID/password/auth не передаём — панель генерирует их сама.
        """
        client = self._get_client()
        payload = {
            "client": {
                "email": email,
                "enable": True,
                "expiryTime": expiry_time_ms,
                "totalGB": total_gb,
                "limitIp": limit_ip,
                "flow": "",
                "security": "auto",
                "comment": "",
                "group": "",
                "tgId": 0,
                "reset": 0,
            },
            "inboundIds": inbound_ids,
        }
        resp = client.post("panel/api/clients/add", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_client_links(self, email: str) -> list[str]:
        """
        Возвращает готовые ссылки-конфиги (vless://, hysteria:// и т.д.)
        для клиента по всем его inbound'ам — те же строки, что в кнопке
        "Copy URL" панели. Собирать вручную ничего не нужно.
        """
        client = self._get_client()
        resp = client.get(f"panel/api/clients/links/{email}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("obj", data) if isinstance(data, dict) else data

    def get_client_traffic(self, email: str) -> dict:
        client = self._get_client()
        resp = client.get(f"panel/api/clients/traffic/{email}")
        resp.raise_for_status()
        return resp.json().get("obj", {})

    def attach_inbounds(self, email: str, inbound_ids: list[int]) -> dict:
        """Прикрепляет существующего клиента к дополнительным inbound'ам."""
        if not inbound_ids:
            return {"success": True}
        client = self._get_client()
        resp = client.post(f"panel/api/clients/{email}/attach", json={"inboundIds": inbound_ids})
        resp.raise_for_status()
        return resp.json()

    def detach_inbounds(self, email: str, inbound_ids: list[int]) -> dict:
        """Открепляет клиента от указанных inbound'ов, не удаляя самого клиента."""
        if not inbound_ids:
            return {"success": True}
        client = self._get_client()
        resp = client.post(f"panel/api/clients/{email}/detach", json={"inboundIds": inbound_ids})
        resp.raise_for_status()
        return resp.json()

    def delete_client(self, email: str, keep_traffic: bool = False) -> dict:
        client = self._get_client()
        params = {"keepTraffic": "1"} if keep_traffic else {}
        resp = client.post(f"panel/api/clients/del/{email}", params=params)
        resp.raise_for_status()
        return resp.json()


# Единственный инстанс на всё приложение — переиспользует TCP-соединение
xui_client = XUIClient()
