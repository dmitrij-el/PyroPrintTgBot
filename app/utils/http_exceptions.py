from datetime import datetime
from typing import Dict, Any

from fastapi import status, HTTPException


class UserAlreadyExistsException(HTTPException):
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Пользователь уже зарегистрирован: {email}',
            headers={"X-Error-Code": '1002'}
        )

class IncorrectPhoneOrEmailException(HTTPException):
    def __init__(self, value: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный формат ввода. Введите email или номер телефона.",
            headers={"X-Error-Code": "1005"}
        )


class NotValidateException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"X-Error-Code": '"1005"'}
        )

class IncorrectEmailOrPasswordException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверная почта или пароль',
            headers={"X-Error-Code": '1003'}
        )

class IncorrectPhoneOrPasswordException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный телефон или пароль',
            headers={"X-Error-Code": '1001'}
        )

class TokenNoFound(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Токен не найден',
            headers={"X-Error-Code": '1011'}
        )

class NoJwtException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Токен не валидный!',
            headers={"X-Error-Code": '1012'}
        )

class TokenExpiredException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Неверный или истекший токен',
            headers={"X-Error-Code": '1013'}
        )


class RefreshTokenExpiredException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Неверный или истекший токен refresh_token.',
            headers={"X-Error-Code": '1014'}
        )

class NoCsrfException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF токен отсутствует или недействителен",
            headers={"X-Error-Code": '1015'}
        )

class ForbiddenAccessException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав!",
            headers={"X-Error-Code": "1011"}
        )

class ForbiddenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Недостаточно прав!',
            headers={"X-Error-Code": '1011'}
        )

class NoUserIdException(HTTPException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Не найден ID пользователя: {user_id}',
            headers={"X-Error-Code": '1007'}
        )

class UserNotFoundException(HTTPException):
    def __init__(self, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Пользователь не найден',
            headers={"X-Error-Code": '1007'}
        )

class IsBannedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Пользователь заблокирован!',
            headers={"X-Error-Code": '1009'}
        )


class InvalidLinkDomainError(HTTPException):
    def __init__(self, link_domain: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Домен уже зарегистрирован: {link_domain}",
            headers={"X-Error-Code": '1202'}
        )

class InvalidCheckLinkError(HTTPException):
    def __init__(self, link_domain: str, link: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Домен {link_domain} не был подтвержден. Верификационный код не был найден на странице: {link}",
            headers={"X-Error-Code": '1202'}
        )


class ValidErrorException(HTTPException):
    def __init__(self, mess):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=mess,
            headers={"X-Error-Code": "1005"}
        )

class BadRequestException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Плохой запрос",
            headers={"X-Error-Code": '1202'}
        )

class BadRequestFileException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Что-то пошло не так. Не подходящий формат или битый файл.",
            headers={"X-Error-Code": '1402'}
        )

class GenerationScriptError(HTTPException):
    def __init__(self, mess: str = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при генерации скрипта{f': {mess}' if mess else None}",
            headers={"X-Error-Code": '1501'}
        )

class InvalidLinkPageError(HTTPException):
    def __init__(self, link_page: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Страница уже зарегистрирована: {link_page}",
            headers={"X-Error-Code": '1203'}
        )

class CatalogBadRequestException(HTTPException):
    def __init__(self, action, mess):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{action.capitalize()}: {mess}. [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
            headers={"X-Error-Code": '1104'}
        )

class CatalogValidError(HTTPException):
    def __init__(self, exp):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {exp}. [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
            headers={"X-Error-Code": '1122'}
        )

class CatalogFatalError(HTTPException):
    def __init__(self, action, mess: str = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fatal {action}{': ' + mess if mess else ''}. [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
            headers={"X-Error-Code": '1100'}
        )

class ObjectNotFoundException(HTTPException):
    def __init__(self, action, obj_name: str, user_id: int, identifier=None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not Found (user_id: {user_id} {action} {obj_name}{f': {identifier}' if identifier else None}). [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
            headers={"X-Error-Code": '1104'}
        )

class CatalogFatalDataError(HTTPException):
    def __init__(self, action, data: Dict[str, Any], mess: str = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fatal {action}{': ' + mess if mess else ''}. [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
            headers={"X-Error-Code": '1100'}
        )

