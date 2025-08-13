# app/bot/__init__.py

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram_sqlite_storage.sqlitestore import SQLStorage
from app.core.config import bot_token_env, debug_mode, get_webhooks_setting, webhook_token_env, fsm_storage
from .middlewares import setup_middlewares
from .handlers import register_routers
from app.utils.logger import logger

# Инициализация бота и диспетчера
bot = Bot(token=bot_token_env(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=SQLStorage(db_path=fsm_storage()))

# Инициализация middleware и роутеров один раз
setup_middlewares(dp)
register_routers(dp)

async def setup_webhook():
    """Настройка вебхука (для production)"""
    if not debug_mode():
        try:
            info = await bot.get_webhook_info()
            if info.url != f"{get_webhooks_setting().WEBHOOK_URL}{get_webhooks_setting().WEBHOOK_PATH}":
                await bot.set_webhook(
                    url=f"{get_webhooks_setting().WEBHOOK_URL}{get_webhooks_setting().WEBHOOK_PATH}",
                    secret_token=webhook_token_env(),
                    drop_pending_updates=True,
                    allowed_updates=[
                        "message",
                        "edited_message",
                        "callback_query",
                        "inline_query",
                        "chat_member",
                        "my_chat_member",
                    ]
                )
            logger.info("✅ Webhook установлен успешно")
        except TelegramRetryAfter as e:
            logger.warning(f"⏳ Превышен лимит запросов Telegram, повторить через {e.retry_after} сек.")
        except TelegramBadRequest as e:
            logger.error(f"❌ Ошибка установки вебхука: {e.message}")
        except Exception as e:
            logger.critical(f"💥 Неизвестная ошибка при установке webhook: {e}")

async def remove_webhook():
    """Удаление вебхука"""
    if not debug_mode():
        await bot.delete_webhook()
        logger.info("Webhook removed")
    await bot.session.close()

async def start_polling():
    """Запуск бота в polling режиме (для разработки)"""
    logger.warning("Running in DEBUG mode (polling)")
    await bot.delete_webhook()
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Polling failed: {e}")
        raise