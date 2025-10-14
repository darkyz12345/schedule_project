from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from db.models.models import AdminUser
from tools import PasswordHasher
from db import get_session
from config import Settings

# --- Загружаем настройки ---
settings = Settings()

# --- Подключение к Redis ---
redis = Redis.from_url(settings.get_redis_url(), decode_responses=True)

# --- JWT параметры ---
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# --- Работа с паролями ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return PasswordHasher.verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return PasswordHasher.hash_password(password)


# --- Создание токенов ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- Декодирование токена ---
def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# --- Управление отзывом токенов ---
async def revoke_token(token: str, expires_in: int):
    """
    Сохраняет токен в Redis как отозванный.
    TTL задаётся так, чтобы Redis автоматически очищал истёкшие токены.
    """
    await redis.setex(f"revoked:{token}", expires_in, "true")


async def is_token_revoked(token: str) -> bool:
    """Проверяет, есть ли токен среди отозванных"""
    return await redis.exists(f"revoked:{token}") == 1


# --- Аутентификация пользователя ---
async def authenticate_user(username: str, password: str, db: AsyncSession) -> Optional[AdminUser]:
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == username, AdminUser.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return None

    return user


# --- Получение текущего пользователя ---
async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session)
) -> AdminUser:
    """
    Получение текущего пользователя по JWT токену
    Поддерживает токен из заголовка Authorization или cookies
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Если токен не из заголовка, пробуем достать из cookie
    if not token:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            token = cookie_token.replace("Bearer ", "")

    if not token:
        raise credentials_exception

    # Проверка отзыва токена
    if await is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен отозван",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Декодируем JWT
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    if not username:
        raise credentials_exception

    # Проверяем пользователя
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == username, AdminUser.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    # Обновляем дату последнего входа
    user.last_login = datetime.now()
    await db.commit()

    return user
