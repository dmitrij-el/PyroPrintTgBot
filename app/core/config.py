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

📚 Где какой конфиг и зачем он нужен?
--------------------------------------

🔹 `AppMetaSettings` — режим работы приложения. Используется через `get_app_settings()`.
🔹 `CorsSettings` — CORS-источники и разрешённые User-Agent'ы. `get_cors_settings()`.
🔹 `UrlsToServices` — URL-ы к внешним микросервисам. `get_urls_to_services()`.
🔹 `IPsToServices` — IP-адреса сервисов (например, для nginx или прямых запросов). `get_ips_to_services()`.
🔹 `ApiTokens` — JWT-секреты и алгоритм. Доступ через:
    - `access_token_env()`
    - `site_token_env()`
    - `algorithm_env()`
🔹 `ProjectPathSettings` — базовые пути: логи, статика, шаблоны, фото. `get_project_path_settings()` или `get_bit_by_bit_config()`.
🔹 `PstgrCatalogBaseSettings` — параметры подключения к PostgreSQL. `get_pstgr_settings()`.
🔹 `RabbitMqSetting` — доступ к RabbitMQ (user, pass, host, port). `get_rabbitmq_settings()`.
🔹 `RedisSetting` — URL-ы Redis по индексам. `get_redis_settings()`.
🔹 `S3StorageConfig` — MinIO + директория с фото. `get_s3_storage_config()`.
🔹 `CatalogFlowerSettings` — логин и пароль для Flower. `get_catalog_flower_settings()`.
🔹 `MailSenderConfig` — SMTP для отправки писем. `get_mail_sender_config()`.

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
    TESTING = "test"

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
        "https://anwill.fun",
        "https://dev.anwill.fun",
        "http://localhost",
        "https://beahea.ru"
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
    WEBHOOK_URL: str = "https://tb.anwill.fun"


class UrlsToServices(Settings):
    DOMAIN_URL: str
    BASE_CATALOG_API_URL: str
    BASE_PLATFORM_API_URL: str
    BASE_USER_API_URL: str
    BASE_MEDIA_IMGS_URL: str
    BASE_MEDIA_CONTENT_URL: str
    BASE_WIDGET_MEDIA_CONTENT_URL: str
    BASE_WIDGET_URL: str
    TG_SERVICE_NOTIFIER_API_URL: str


class IPsToServices(Settings):
    BASE_CATALOG_API_IP: str
    BASE_PLATFORM_API_IP: str
    BASE_USER_API_IP: str
    BASE_MEDIA_IP: str
    TG_SERVICE_NOTIFIER_API_IP: str


class TokensConfig(Settings):
    TOKEN_ACCESS_SECRET_KEY: SecretStr
    WEBHOOK_SECRET_KEY: SecretStr
    BOT_TOKEN: SecretStr
    ALGORITHM: str = "HS256"


class ProjectPathSettings(Settings):
    BASE_LOGS_PATH: Path = BASE_PATH / "logs"
    BASE_STATIC_PATH: Path = BASE_PATH / "app/frontend/static"
    BASE_TEMPLATES_PATH: Path = BASE_PATH / "app/frontend/templates"
    BASE_PHOTO_PATH: Path = BASE_PATH / "imgs"
    FSM_STORAGE_PATH: Path = BASE_PATH / "fsm-storage"

    @property
    def static_mounts(self) -> dict[str, Path]:
        return {
            "static": self.BASE_STATIC_PATH,
            "imgs": self.BASE_PHOTO_PATH,
            "logs": self.BASE_LOGS_PATH,
            "fsm-storage": self.FSM_STORAGE_PATH,
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.BASE_LOGS_PATH.mkdir(parents=True, exist_ok=True)
        self.BASE_STATIC_PATH.mkdir(parents=True, exist_ok=True)
        self.BASE_TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)
        self.BASE_PHOTO_PATH.mkdir(parents=True, exist_ok=True)
        self.FSM_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

class PstgrCatalogBaseSettings(Settings):
    CATALOG_PSTGR_USER: str
    CATALOG_PSTGR_PASS: SecretStr
    CATALOG_PSTGR_NAME: str
    CATALOG_PSTGR_HOST: str
    CATALOG_PSTGR_PORT: str

    @property
    def async_catalog_pstgr_url(self) -> str:
        return f"postgresql+asyncpg://{self.CATALOG_PSTGR_USER}:{self.CATALOG_PSTGR_PASS.get_secret_value()}@{self.CATALOG_PSTGR_HOST}:{self.CATALOG_PSTGR_PORT}/{self.CATALOG_PSTGR_NAME}"

    @property
    def sync_catalog_pstgr_url(self) -> str:
        return f"postgresql://{self.CATALOG_PSTGR_USER}:{self.CATALOG_PSTGR_PASS.get_secret_value()}@{self.CATALOG_PSTGR_HOST}:{self.CATALOG_PSTGR_PORT}/{self.CATALOG_PSTGR_NAME}"


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
def get_pstgr_settings() -> PstgrCatalogBaseSettings:
    return PstgrCatalogBaseSettings()


@lru_cache()
def get_urls_to_services() -> UrlsToServices:
    return UrlsToServices()


@lru_cache()
def get_ips_to_services() -> IPsToServices:
    return IPsToServices()


@lru_cache()
def get_bit_by_bit_config() -> ProjectPathSettings:
    return ProjectPathSettings()

@lru_cache()
def get_webhooks_setting() -> WebhookSettings:
    return WebhookSettings()

@lru_cache()
def access_token_env() -> str:
    return TokensConfig().TOKEN_ACCESS_SECRET_KEY.get_secret_value()

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
def base_api_user_url() -> str:
    return UrlsToServices().BASE_USER_API_URL


@lru_cache()
def base_photo_path() -> Path:
    return ProjectPathSettings().BASE_PHOTO_PATH
