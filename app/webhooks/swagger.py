# app/webhooks/swagger.py
import httpx
from fastapi import Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from jose import jwt

from app.core.config import BASE_PATH, base_api_user_url, algorithm_env, access_token_env
from app.utils.logger import logger

oauth2_scopes = {
    "USER": "Стандартный пользовательский доступ.",
    "DEVELOPER": "Доступ для разработчиков",
    "ADMIN": "Администраторский доступ с ограничениями.",
    "SYSADMIN": "Администраторский доступ без ограничений.",
    "MANAGER": "Менеджерский доступ",
    "SUPPORT": "Доступ для тех.поддержки",
    "MODERATOR": "Доступ для модераторов"
}

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{base_api_user_url()}login",
    scopes=oauth2_scopes,
    scheme_name="JWT Bearer Token",  # Название схемы безопасности, которое будет видно в OpenAPI
    description="""
    OAuth2 схема аутентификации с использованием JWT токена. Эндпоинт авторизации поддерживает два типа грантов: 
    1. **`password`** - аутентификация с использованием имени пользователя (email или телефон) и пароля.
    2. **`refresh_token`** - обновление токена доступа с помощью предоставленного refresh_token.

    Для получения токенов доступа (access_token) и обновления токенов (refresh_token) используется следующая логика:
    - При `grant_type=password` генерируется новый `access_token` (сроком на 30 минут) и `refresh_token`.
    - При `grant_type=refresh_token` обновляется `access_token` и возвращается новый `refresh_token` в cookies.

    Необходимость в предоставлении токена актуальна для всех защищенных эндпоинтов.
    """
)

templates = Jinja2Templates(directory=str(BASE_PATH / "app/frontend/templates"))

class ProtectedSwagger:
    def __init__(self):
        # Все базовые пути, где нужно защитить документацию
        self.protected_paths = [
            "",
            "/update",
            "/notifications",
        ]

    async def is_swagger_path(self, path: str) -> bool:
        """Проверяет, относится ли путь к документации"""
        for base_path in self.protected_paths:
            if path == f"{base_path}/docs" or path == f"{base_path}/redoc":
                return True
            if path == f"{base_path}/openapi.json":
                return True
        return False

    @staticmethod
    async def swagger_login_page(request: Request):
        return templates.TemplateResponse(
            "swagger_login.html",
            {"request": request, "error": request.method == "POST"}
        )

    @staticmethod
    async def check_auth(request: Request):
        # Проверяем куки Swagger
        authorized = request.cookies.get("swagger_authorized")
        if authorized == "true":
            return True

        # Проверяем JWT токен из запроса
        try:
            token = await oauth2_scheme(request)
            payload = jwt.decode(token, access_token_env(), algorithms=[algorithm_env()])
            user_scopes = payload.get("scopes", [])
            # Обновленный список разрешенных ролей
            required_scopes = {"USER", "ADMIN", "SYSADMIN", "DEVELOPER"}
            if any(scope in user_scopes for scope in required_scopes):
                return True
        except Exception:
            pass

        return False

    async def process_request(self, request: Request, call_next):
        path = request.url.path

        # Пропускаем все пути, не связанные с документацией
        if not await self.is_swagger_path(path):
            return await call_next(request)

        # Для openapi.json пропускаем без проверки
        if path.endswith("openapi.json"):
            return await call_next(request)

        # Проверяем авторизацию
        if request.method == "POST" and path.endswith(("/docs", "/redoc")):
            form_data = await request.form()
            username = form_data.get("username")
            password = form_data.get("password")


            if await self.authenticate_via_oauth(username, password):
                # Разрешаем доступ после успешной OAuth2 аутентификации
                response = RedirectResponse(url=path, status_code=status.HTTP_303_SEE_OTHER)
                response.set_cookie(
                    key="swagger_authorized",
                    value="true",
                    httponly=True,
                    secure=True,
                    samesite='lax',
                    max_age=3600
                )
                return response
            else:
                if "application/json" in request.headers.get("accept", ""):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Access denied. Insufficient privileges or invalid credentials"}
                    )
                return await self.swagger_login_page(request)

        # Проверяем куки или JWT токен для GET-запросов
        if not await self.check_auth(request):
            return await self.swagger_login_page(request)

        return await call_next(request)

    @staticmethod
    async def authenticate_via_oauth(username: str, password: str) -> bool:
        """Аутентификация через OAuth2 endpoint с проверкой ролей"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_api_user_url()}login",
                    data={
                        "username": username,
                        "password": password,
                        "grant_type": "password",
                        "scope": "USER DEVELOPER"  # Запрашиваемые scope
                    }
                )

                if response.status_code == 200:
                    token_data = response.json()
                    # Декодируем токен для проверки scope
                    payload = jwt.decode(
                        token_data["access_token"],
                        access_token_env(),
                        algorithms=[algorithm_env()]
                    )
                    user_scopes = payload.get("scopes", [])
                    # Проверяем, есть ли у пользователя нужные права
                    required_scopes = {"USER"}
                    return any(scope in user_scopes for scope in required_scopes)

            return False
        except Exception as e:
            logger.error(f"OAuth2 authentication error: {str(e)}")
            return False
