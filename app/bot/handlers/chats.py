# app/bot/handlers/user_chats.py
from datetime import datetime, timezone, timedelta

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.bot.decorators import bot_error_handler
from app.utils.logger import logger
from app.db.models.tb_models import TelegramUser, TelegramChat, TGKeys
from app.db.schemas.tb_schemas import ChatCreate
from app.db.sessions.utils import async_connect_db

router = Router()




@router.message(CommandStart())
@async_connect_db(commit=True)
@bot_error_handler
async def handle_start(message: Message, db: AsyncSession):
    try:
        from_user = message.from_user
        chat = message.chat
        logger.info(f"/start от {from_user.id} в чате {chat.id} ({chat.type})")

        # === ЕСЛИ ПРИВАТНЫЙ ЧАТ: создаем пользователя ===
        if chat.type == "private":
            logger.info('1. Работаем в приватном чате. Получаем или создаем пользователя.')

            # Получаем пользователя без загрузки токена (пока)
            stmt = select(TelegramUser).where(TelegramUser.telegram_id == from_user.id)
            user = (await db.execute(stmt)).scalar_one_or_none()

            if user:
                logger.info('   Обновляем данные пользователя')
                user.first_name = from_user.first_name
                user.last_name = from_user.last_name
                user.username = from_user.username
                user.language_code = from_user.language_code
                logger.info(f"  Обновлен пользователь: {user.telegram_id}")
            else:
                logger.info('   Создаем нового пользователя')
                user = TelegramUser(
                    telegram_id=from_user.id,
                    is_bot=from_user.is_bot,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    username=from_user.username,
                    language_code=from_user.language_code
                )
                db.add(user)
                logger.info(f"   Создан пользователь: {user.telegram_id}")

            logger.info("2. Фиксируем изменения в БД для пользователя")
            await db.flush()

            logger.info("3. Проверяем наличие токена")
            # Отдельный запрос для проверки токена
            token_stmt = select(TGKeys).where(TGKeys.tg_user_id == user.id)
            existing_token = (await db.execute(token_stmt)).scalar_one_or_none()

            if not existing_token:
                logger.info("   Создаем новый токен")
                verification_key = TGKeys(tg_user_id=user.id)
                db.add(verification_key)
                await db.flush()
                logger.info(f"   Создан токен для пользователя: {user.telegram_id}")
            else:
                logger.info("   Обновляем срок действия токена")
                existing_token.expires_at = datetime.now(timezone.utc) + timedelta(days=3)
                logger.info(f"   Обновлен токен пользователя: {user.telegram_id}")

            logger.info("4. Получаем полные данные с токеном")
            full_stmt = (
                select(TelegramUser)
                .options(selectinload(TelegramUser.verification_key))
                .where(TelegramUser.telegram_id == from_user.id)
            )
            user_with_token = (await db.execute(full_stmt)).scalar_one()

            if not user_with_token.verification_key:
                logger.error("   Токен не был создан")
                raise ValueError("Токен не был создан")

            logger.info("5. Формируем сообщение")
            username = (
                f"@{user_with_token.username}"
                if user_with_token.username
                else f"{user_with_token.first_name} {user_with_token.last_name or ''}".strip()
            ).capitalize()

            welcome_msg = (
                f"🚀 Привет, {username}!\n\n"
                "🔹 <b>Сервис Anwill Telegram FormData</b>\n\n"
                "Для подключения используйте:\n\n"
                f"<b>API Key:</b> <code>{user_with_token.verification_key.api_key}</code>\n"
            )
            await message.answer(welcome_msg, parse_mode="HTML")

        # === ЕСЛИ ГРУППА/СУПЕРГРУППА: регистрируем чат ===
        elif chat.type in ["group", "supergroup"]:
            logger.info("1. Работаем в группе. Регистрируем чат, если не зарегистрирован.")

            stmt = select(TelegramChat).where(TelegramChat.telegram_id == chat.id)
            chat_db = (await db.execute(stmt)).scalar_one_or_none()

            if chat_db:
                logger.info(f'   Обновляем данные {chat_db.type}')
                chat_db.type = chat_db.type
                chat_db.title = chat_db.title
                chat_db.username = chat_db.username
                chat_db.first_name = chat_db.first_name
                chat_db.last_name = chat_db.last_name
                chat_db.is_forum = chat_db.is_forum
                chat_db.invite_link = chat_db.invite_link
                chat_db.photo_id = chat_db.photo_id
                chat_db.is_active = True
                logger.info(f"  Обновлен {chat_db.type}: {chat_db.telegram_id}")

            else:
                chat_data = ChatCreate.from_telegram(chat)
                logger.info(f'   Создаем новый {chat_data.type}')
                chat_db = TelegramChat(
                    telegram_id=chat_data.telegram_id,
                    type=chat_data.type,
                    title=chat_data.title,
                    username=chat_data.username,
                    first_name=chat_data.first_name,
                    last_name=chat_data.last_name,
                    is_forum=chat_data.is_forum,
                    invite_link=chat_data.invite_link,
                    photo_id=chat_data.photo_id,
                )
                db.add(chat_db)
                logger.info(f"   Создан {chat_db.type}: {chat_db.telegram_id}")

            logger.info(f"2. Фиксируем изменения в БД для {chat_db.type}")
            await db.flush()

            logger.info("3. Проверяем наличие токена")
            token_stmt = select(TGKeys).where(TGKeys.tg_chat_id == chat_db.id)
            existing_token = (await db.execute(token_stmt)).scalar_one_or_none()

            if not existing_token:
                logger.info("   Создаем новый токен")
                verification_key = TGKeys(tg_chat_id=chat_db.id)
                db.add(verification_key)
                await db.flush()
                logger.info(f"   Создан токен для {chat_db.type}: {chat_db.telegram_id}")
            else:
                logger.info("   Обновляем срок действия токена")
                existing_token.expires_at = datetime.now(timezone.utc) + timedelta(days=36000)
                logger.info(f"   Обновлен токен пользователя: {chat_db.telegram_id}")

            logger.info("4. Получаем полные данные с токеном")
            full_stmt = (
                select(TelegramChat)
                .options(selectinload(TelegramChat.verification_key))
                .where(TelegramChat.telegram_id == chat.id)
            )
            chat_with_token = (await db.execute(full_stmt)).scalar_one()

            if not chat_with_token.verification_key:
                logger.error("   Токен не был создан")
                raise ValueError("Токен не был создан")

            logger.info("5. Формируем сообщение")
            username = (
                f"@{chat_with_token.username}"
                if chat_with_token.username
                else f"{chat_with_token.first_name} {chat_with_token.last_name or ''}".strip()
            ).capitalize()

            welcome_msg = (
                f"🤖 Бот активирован в группе <b>{chat_with_token.title or 'без названия'}</b>\n\n"
                "Для подключения используйте:\n\n"
                f"<b>API Key:</b> <code>{chat_with_token.verification_key.api_key}</code>\n"
            )
            await message.answer(welcome_msg, parse_mode="HTML")

        else:
            await message.answer("Бот работает только в приватных чатах и группах.")


    except Exception as e:
        logger.error(f"Ошибка в /start: {e}", exc_info=True)
        await message.answer("⚠️ Ошибка обработки запроса. Попробуйте позже.")
        raise


@router.message(Command("my_keys"))
@async_connect_db()
@bot_error_handler
async def get_my_keys(message: Message, db: AsyncSession):
    """Повторная выдача ключей пользователя или чата"""
    try:
        if message.chat.type == 'private':
            # Запрос ключей пользователя
            stmt = (
                select(TelegramUser)
                .where(TelegramUser.telegram_id == message.from_user.id)
                .options(joinedload(TelegramUser.verification_key))
            )
            user: TelegramUser = (await db.execute(stmt)).scalar_one_or_none()

            if user and user.verification_key:
                await message.answer(
                    f"🔑 Ваши ключи:\n\n"
                    f"API: <code>{user.verification_key.api_key}</code>\n",
                    parse_mode="HTML"
                )
            else:
                await message.answer("Вы не зарегистрированы в системе. Отправьте /start")
        else:
            # Запрос ключей чата
            stmt = (
                select(TelegramChat)
                .where(TelegramChat.telegram_id == message.chat.id)
                .options(joinedload(TelegramChat.verification_key))
            )
            chat: TelegramChat = (await db.execute(stmt)).scalar_one_or_none()

            if chat and chat.verification_key:
                await message.answer(
                    f"🔑 Ключи этого чата:\n\n"
                    f"API: <code>{chat.verification_key.api_key}</code>\n",
                    parse_mode="HTML"
                )
            else:
                await message.answer("Этот чат не зарегистрирован в системе. Добавьте бота в чат снова.")

    except Exception as e:
        logger.error(f"Ошибка при запросе ключей: {e}")
        await message.answer("⚠️ Произошла ошибка при получении ключей")


@router.message(Command("reissue_keys"))
@async_connect_db(commit=True)
@bot_error_handler
async def reissue_keys(message: Message, db: AsyncSession):
    """Перевыпуск ключей"""
    try:
        is_private = message.chat.type == 'private'

        if is_private:
            # Работаем с пользователем
            stmt = (
                select(TelegramUser)
                .where(TelegramUser.telegram_id == message.from_user.id)
                .options(joinedload(TelegramUser.verification_key))
            )
            user: TelegramUser = (await db.execute(stmt)).scalar_one_or_none()

            if not user or not user.verification_key:
                await message.answer("Вы не зарегистрированы в системе. Отправьте /start")
                return

            key = user.verification_key

        else:
            # Работаем с чатом
            stmt = (
                select(TelegramChat)
                .where(TelegramChat.telegram_id == message.chat.id)
                .options(joinedload(TelegramChat.verification_key))
            )
            chat: TelegramChat = (await db.execute(stmt)).scalar_one_or_none()

            if not chat or not chat.verification_key:
                await message.answer("Этот чат не зарегистрирован в системе. Добавьте бота в чат снова.")
                return

            key = chat.verification_key

        # Перевыпуск ключей
        import secrets
        from datetime import datetime, timedelta, timezone

        key.api_key = secrets.token_urlsafe(15)
        key.expires_at = datetime.now(timezone.utc) + timedelta(days=36000)

        await db.flush()

        await message.answer(
            f"🔁 Ключи перевыпущены:\n\n"
            f"<b>API Key:</b> <code>{key.api_key}</code>\n",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при перевыпуске ключей: {e}", exc_info=True)
        await message.answer("⚠️ Ошибка при перевыпуске ключей. Попробуйте позже.")



@router.message(F.text.lower() == "хочу присоединиться к проекту")
@bot_error_handler
async def handle_join_request(message: Message):
    # 1. Отвечаем пользователю
    await message.answer(
        "👋 Спасибо за интерес к проекту!\n\n"
        "✅ Мы скоро свяжемся с вами.\n"
        "📚 Ознакомьтесь с документацией:\n"
        "- https://api.anwill.fun/docs\n"
        "- https://api.anwill.fun/catalog/docs\n"
        "- https://tb.anwill.fun/docs\n\n"
        "🌐 Наш сайт: https://anwill.fun\n"
        "🔑 Регистрация: https://id.anwill.fun\n\n"
        "💡 Ожидайте ответа – команда свяжется с вами в ближайшее время. 🚀"
    )

    # 2. Отправляем уведомление 3 администраторам
    contact_info = (
        f"📩 Новый запрос на подключение к проекту:\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"🔗 Username: @{message.from_user.username}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n"
        f"🌍 Язык: {message.from_user.language_code}\n\n"
        f"💬 Текст: {message.text}"
    )

    admin_ids = [723151484, 37437873, 204984112]
    for admin_id in admin_ids:
        await message.bot.send_message(chat_id=admin_id, text=contact_info)

