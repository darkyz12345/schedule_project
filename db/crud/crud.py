from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AdminUser
from tools import PasswordHasher


async def create_admin_user(session: AsyncSession,
                      username: str,
                      email: str,
                      full_name: str,
                      password: str,
                      role: str = 'editor',
                      is_active: bool = False) -> AdminUser:
    """
    Добавляет данные нового администратора
    :param session: Сессия бд
    :param username: логин
    :param email: почта
    :param full_name: имя, фамилия, отчество(по желанию)
    :param password: пароль
    :param role: роль(админ или редактор, по умолчанию редактор)
    :param is_active: активен или нет(по умолчанию нет, нужно рассмотрение со стороны главного админа)
    :return: Администратор
    """
    hashed_password = PasswordHasher.hash_password(password)
    user = AdminUser(username=username,
                     email=email,
                     full_name=full_name,
                     password_hash=hashed_password,
                     role=role,
                     is_active=is_active)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user