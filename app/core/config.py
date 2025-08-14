# app/core/config.py

"""
📦 Конфигурация проекта: зачем и как всё устроено
✅ Что делают `SecretStr` и `.get_secret_value()`?
--------------------------------------------------
- `SecretStr` скрывает значение при логировании и в отладке (`SecretStr('**********')`).
- Защищает чувствительные данные: токены, пароли, ключи.
- Чтобы получить реальное значение, вызывается `.get_secret_value()`.
- Таким образом, случайный `print()` или логгер не покажет секрет.

✅ Зачем нужен `EmailStr`?
---------------------------
- Тип из Pydantic с валидацией email при загрузке.
- Предотвращает ошибки — невалидные адреса не пройдут.

✅ Почему используется `pydantic_settings.BaseSettings`?
---------------------------------------------------------
- Все переменные окружения строго типизированы и валидируются.
- .env-файл подключается автоматически (через Config).
- Удобно работать с разными окружениями: dev, prod, test.
- Ошибки конфигурации ловятся сразу при старте проекта.

✅ Зачем нужны lazy-обёртки с `@lru_cache`?
------------------------------------------
- Настройки и .env загружаются один раз — никакой лишней работы.
- Нет глобальных переменных — вызов в любом месте через `get_*_settings()`.
- Устойчиво к циклическим импортам.
- Легко протестировать или подменить конфиг.


🧠 Использование:
    from app.core.config import get_db_settings
    db = get_db_settings().async_catalog_pstgr_url
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, SecretStr
from pydantic_settings import BaseSettings

BASE_PATH = Path(__file__).resolve().parent.parent.parent


class TypeNetwork(str, Enum):
    LOCAL = "local"
    SERVER = "server"

class TypeServer(str, Enum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"

class Settings(BaseSettings):
    class Config:
        env_file = BASE_PATH / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

class AppMetaSettings(Settings):
    TYPE_NETWORK: str = TypeNetwork.LOCAL
    TYPE_SERVER: str = TypeServer.DEVELOPMENT

    @property
    def get_debug_mode(self) -> bool:
        return self.TYPE_NETWORK == TypeNetwork.LOCAL

class CorsSettings(Settings):
    CORS_ALLOWED_ORIGINS: set[str] = {
        "localhost"
    }
    VALID_USER_AGENTS: list[str] = [
        r"Chrome/\d+\.\d+\.\d+\.\d+",
        r"Firefox/\d+\.\d+",
        r"Safari/\d+\.\d+",
        r"Mobile Safari/\d+\.\d+",
        r"OPR/\d+\.\d+",
        r"Edge/\d+\.\d+",
        r"EdgA/\d+\.\d+",
        r"SamsungBrowser/\d+\.\d+",
    ]

class WebhookSettings(Settings):
    WEBHOOK_PATH: str = "/updates"
    WEBHOOK_URL: str = "https://pyro-print.beahea.ru"

class TokensConfig(Settings):
    WEBHOOK_SECRET_KEY: SecretStr
    BOT_TOKEN: SecretStr
    ALGORITHM: str = "HS256"

class ProjectPathSettings(Settings):
    BASE_LOGS_PATH: Path = BASE_PATH / "logs"
    BASE_PHOTO_PATH: Path = BASE_PATH / "imgs"
    FSM_STORAGE_PATH: Path = BASE_PATH / "fsm-storage"

    @property
    def static_mounts(self) -> dict[str, Path]:
        return {
            "imgs": self.BASE_PHOTO_PATH,
            "logs": self.BASE_LOGS_PATH,
            "fsm-storage": self.FSM_STORAGE_PATH,
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.BASE_LOGS_PATH.mkdir(parents=True, exist_ok=True)
        self.BASE_PHOTO_PATH.mkdir(parents=True, exist_ok=True)
        self.FSM_STORAGE_PATH.mkdir(parents=True, exist_ok=True)



# Lazy обёртки
@lru_cache()
def get_app_settings() -> AppMetaSettings:
    return AppMetaSettings()

@lru_cache()
def debug_mode() -> bool:
    return AppMetaSettings().get_debug_mode


@lru_cache()
def get_cors_settings() -> CorsSettings:
    return CorsSettings()

@lru_cache()
def get_project_path_settings() -> ProjectPathSettings:
    return ProjectPathSettings()

@lru_cache()
def fsm_storage() -> str:
    return str(ProjectPathSettings().FSM_STORAGE_PATH / "storage.db")

@lru_cache()
def get_webhooks_setting() -> WebhookSettings:
    return WebhookSettings()


@lru_cache()
def bot_token_env() -> str:
    return TokensConfig().BOT_TOKEN.get_secret_value()

@lru_cache()
def webhook_token_env() -> str:
    return TokensConfig().WEBHOOK_SECRET_KEY.get_secret_value()

@lru_cache()
def algorithm_env() -> str:
    return TokensConfig().ALGORITHM


@lru_cache()
def base_photo_path() -> Path:
    return ProjectPathSettings().BASE_PHOTO_PATH
