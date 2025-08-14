# app/bot/handlers/__init__.py

from aiogram import Dispatcher

from app.bot.handlers.chats import router as start_router
from app.utils.logger import logger


def register_routers(dp: Dispatcher):
    logger.info("Регистрация всех роутеров")
    dp.include_router(start_router)
