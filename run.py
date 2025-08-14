# app/run.py
import os
import uvicorn
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Update
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import BASE_PATH, debug_mode, get_cors_settings, get_webhooks_setting, get_project_path_settings
from app.bot import bot, dp, setup_webhook, remove_webhook, start_polling
from app.utils.logger import logger
from app.webhooks.handlers import router



@asynccontextmanager
async def lifespan(application: FastAPI):
    if debug_mode():
        import asyncio
        asyncio.create_task(start_polling())
    else:
        # Только первый Gunicorn worker выполняет setup_webhook
        worker_id = os.getenv("WORKER_ID")
        logger.info(f"🐙 Worker ID = {worker_id}")
        if worker_id is None or worker_id == "0":
            logger.info(f"🐙*** {worker_id} ВОРКЕР GUVICORN ВЫПОЛНЯЕТ setup_webhook ***")
            await setup_webhook()

    yield

    if not debug_mode():
        # Только первый worker убирает вебхук
        worker_id = os.getenv("WORKER_ID")
        if worker_id is None or worker_id == "0":
            logger.info(f"🐙*** {worker_id} ВОРКЕР GUVICORN ВЫПОЛНЯЕТ setup_webhook ***")
            await remove_webhook()


app = FastAPI(
    lifespan=lifespan,
    redirect_slashes=True,
    title="PyroPrint",
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
    swagger_ui_init_oauth={
        "clientId": "swagger-client",
        "appName": "Swagger UI PyroPrint",
        "scopes": "USER DEVELOPER",  # Используем явно заданные роли
        "usePkceWithAuthorizationCodeGrant": True,
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_settings().CORS_ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

for route, path in get_project_path_settings().static_mounts.items():
    app.mount(f"/{route}", StaticFiles(directory=path), name=route)


app.include_router(router)


@app.post(get_webhooks_setting().WEBHOOK_PATH)
async def handle_webhook(request: Request):
    try:
        # 1. Парсинг входящего JSON
        try:
            json_data = await request.json()
            update = Update.model_validate(json_data)
        except ValidationError as ve:
            logger.error(f"Validation error: {ve}")
            raise HTTPException(status_code=422, detail="Invalid update format")
        except Exception as exp:
            logger.error(f"JSON parsing error: {exp}")
            raise HTTPException(status_code=400, detail="Malformed JSON data")

        # 2. Обработка обновления
        try:
            await dp.feed_update(bot, update)
        except TelegramAPIError as te:
            logger.error(f"Telegram API error: {te}")
            raise HTTPException(
                status_code=502,
                detail=f"Telegram API error: {te.message}"
            )
        except SQLAlchemyError as se:
            logger.critical(f"Database error: {se}")
            await request.app.state.db_session.rollback()
            raise HTTPException(
                status_code=503,
                detail="Database operation failed"
            )
        except Exception as exp:
            logger.error(f"Unexpected processing error: {exp}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )

        return JSONResponse(
            status_code=200,
            content={"status": "ok"},
            headers={"X-Webhook-Processed": "true"}
        )

    except HTTPException as http_exp:
        # Уже обработанные ошибки
        raise http_exp
    except Exception as exp:
        # Неожиданные ошибки верхнего уровня
        logger.critical(f"Critical webhook failure: {exp}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import asyncio
    import sys

    try:
        uvicorn.run(
            "run:app",
            host="0.0.0.0",
            port=49556,
            reload=True,
            proxy_headers=True,
            factory=False,
        )
    except asyncio.CancelledError:
        print("🛑 Сервер остановлен (CancelledError)")
        sys.exit(0)
    except KeyboardInterrupt:
        print("🛑 Сервер остановлен пользователем (CTRL+C)")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
        sys.exit(1)
