from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = "insecure-dev-key-change-me"

    xui_panel_url: str = "https://127.0.0.1:2053/"
    xui_api_token: str = ""

    database_url: str = "sqlite:///./data/site.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # не падать, если в .env остались старые/лишние переменные
    )


settings = Settings()
