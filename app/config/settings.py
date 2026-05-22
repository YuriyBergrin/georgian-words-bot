from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    admin_telegram_ids: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")

    @property
    def admin_ids_set(self) -> set[int]:
        return {
            int(value.strip())
            for value in self.admin_telegram_ids.split(",")
            if value.strip()
        }


settings = Settings()
