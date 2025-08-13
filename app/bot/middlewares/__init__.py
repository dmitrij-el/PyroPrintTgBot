# app/bot/middlewares/__init__.py

from aiogram import Dispatcher
from .logging import LoggingMiddleware
from .throttling import ThrottlingMiddleware
from app.utils.logger import logger

def setup_middlewares(dp: Dispatcher):
    logger.info("Регистрация всех middleware")
    dp.update.outer_middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_limit=2))