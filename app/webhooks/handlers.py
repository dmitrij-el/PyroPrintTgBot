from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import logger
from app.bot import bot
from app.db.models.tb_models import TelegramUser
from app.db.schemas.tb_schemas import NotificationRequest
from app.db.sessions.utils import SessionDep

router = APIRouter(prefix="/notifier", tags=["Notifications"])


@router.post("/send")
async def notify_user(
        request: NotificationRequest,
        session: AsyncSession = SessionDep
):
    try:
        stmt = select(TelegramUser).where(TelegramUser.telegram_id.in_(request.telegram_id))
        result = await session.execute(stmt)
        tg_contacts = result.scalars().all()

        if not tg_contacts:
            raise HTTPException(status_code=404, detail="Контакты Telegram не найдены")

        for contact in tg_contacts:
            await bot.send_message(
                chat_id=contact.telegram_id,
                text=request.message,
                parse_mode="HTML"  # если нужно
            )

        logger.info(f'Сообщения отправлены пользователям: {", ".join(str(u.telegram_id) for u in tg_contacts)}')
        return {"detail": "Все сообщения успешно отправлены"}

    except Exception as e:
        logger.exception("Ошибка при отправке сообщений в Telegram")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при отправке уведомлений")