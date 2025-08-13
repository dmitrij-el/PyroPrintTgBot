from http.client import HTTPException
from typing import Callable, Coroutine, Any, TypeVar
from functools import wraps

from aiogram import types
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import SQLAlchemyError

from app.utils.logger import logger
from app.db.models.tb_models import TelegramUser, TelegramChat

T = TypeVar('T', TelegramUser, TelegramChat)

def bot_error_handler(func: Callable[..., Coroutine[Any, Any, None]]):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        try:
            return await func(message, *args, **kwargs)
        except HTTPException as http_exp:
            return http_exp
        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}", exc_info=True)
            await message.answer("⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.")
        except SQLAlchemyError as e:
            logger.critical(f"Database error: {e}", exc_info=True)
            await message.answer("🔧 Технические неполадки. Мы уже работаем над решением.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await message.answer("❌ Произошла непредвиденная ошибка. Администратор уведомлен.")

    return wrapper


