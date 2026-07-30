from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "insecure-dev-key-change-me"

    xui_panel_url: str = "https://127.0.0.1:2053/"
    xui_username: str = ""
    xui_password: str = ""
    xui_api_token: str = ""

    public_server_address: str = "your-server-ip-or-domain"

    database_url: str = "sqlite:///./data/site.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
