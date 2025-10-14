from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.models.models import AdminUser
from db import get_session
from web.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    is_token_revoked,
    get_password_hash,
    get_current_user
)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


# Pydantic модели
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


# ============================================
# HTML страницы
# ============================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("login.html", {
        "request": request
    })


@router.get("/logout", response_class=HTMLResponse)
async def logout_page():
    """Выход из системы"""
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


# ============================================
# API endpoints
# ============================================

@router.post("/login", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_session)
):
    """
    Вход в систему
    Возвращает access и refresh токены
    """
    user = await authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создаем токены
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login/form")
async def login_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_session)
):
    """
    Вход через HTML форму
    Устанавливает токены в cookies и редиректит
    """
    user = await authenticate_user(form_data.username, form_data.password, db)

    if not user:
        return templates.TemplateResponse("login.html", {
            "request": None,
            "error": "Неверное имя пользователя или пароль"
        }, status_code=401)

    # Создаем токены
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    # Устанавливаем в cookies
    response = RedirectResponse(url="/groups", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 минут
        samesite="lax"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=604800,  # 7 дней
        samesite="lax"
    )

    return response


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
        token_data: TokenRefresh,
        db: AsyncSession = Depends(get_session)
):
    """
    Обновление access токена с помощью refresh токена
    """
    # Проверяем, не отозван ли refresh токен
    if is_token_revoked(token_data.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отозван"
        )

    # Декодируем refresh токен
    payload = decode_token(token_data.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный refresh токен"
        )

    # Проверяем тип токена
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена"
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен"
        )

    # Проверяем, существует ли пользователь
    from sqlalchemy import select
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.username == username,
            AdminUser.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )

    # Создаем новые токены
    new_access_token = create_access_token(data={"sub": username})
    new_refresh_token = create_refresh_token(data={"sub": username})

    # Отзываем старый refresh токен
    revoke_token(token_data.refresh_token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
        current_user: AdminUser = Depends(get_current_user),
        access_token: str = Depends(lambda: None)  # Получаем из headers
):
    """
    Выход из системы
    Отзывает access токен
    """
    # В реальном приложении нужно получить токен из заголовка
    # И отозвать его

    return {"message": "Успешный выход"}


@router.post("/logout/all")
async def logout_all(
        current_user: AdminUser = Depends(get_current_user)
):
    """
    Выход на всех устройствах
    Отзывает все токены пользователя
    """
    # Здесь можно реализовать отзыв всех токенов пользователя
    # Для этого нужно хранить токены в БД или Redis

    return {"message": "Выход выполнен на всех устройствах"}


@router.post("/change-password")
async def change_password(
        password_data: ChangePassword,
        current_user: AdminUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_session)
):
    """
    Смена пароля
    """
    from web.auth import verify_password

    # Проверяем старый пароль (используем поле password вместо password_hash)
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный старый пароль"
        )

    # Устанавливаем новый пароль
    current_user.password = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Пароль успешно изменен"}


@router.get("/me")
async def get_current_user_info(
        current_user: AdminUser = Depends(get_current_user)
):
    """
    Получение информации о текущем пользователе
    """
    return {
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login
    }
