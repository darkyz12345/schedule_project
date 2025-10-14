import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from db import get_session
from db.models import AdminUser
from tools import PasswordHasher


async def create_admin():
    """Создание администратора с правами доступа"""

    print("=" * 60)
    print("🔐 Создание администратора веб-панели")
    print("=" * 60)
    print()

    # Ввод данных
    username = input("Имя пользователя: ").strip()
    if not username:
        print("❌ Имя пользователя не может быть пустым")
        return

    email = input("Email: ").strip()
    if not email:
        print("❌ Email не может быть пустым")
        return

    password = input("Пароль (минимум 6 символов): ").strip()
    if len(password) < 6:
        print("❌ Пароль должен быть минимум 6 символов")
        return

    password_confirm = input("Подтвердите пароль: ").strip()
    if password != password_confirm:
        print("❌ Пароли не совпадают")
        return

    full_name = input("Полное имя: ").strip()
    if not full_name:
        print("❌ Полное имя не может быть пустым")
        return

    # Роль
    print("\nВыберите роль:")
    print("1. admin - полный доступ")
    print("2. editor - редактирование (по умолчанию)")
    role_choice = input("Введите номер (1-2) [2]: ").strip()
    role = "admin" if role_choice == "1" else "editor"

    # Активность
    is_active_input = input("\nАктивировать сразу? (y/n) [y]: ").strip().lower()
    is_active = is_active_input != 'n'

    # Создаем в БД
    async for session in get_session():
        # Проверяем, существует ли пользователь
        from sqlalchemy import select
        result = await session.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"❌ Пользователь '{username}' уже существует")
            return

        # Хешируем пароль через ваш класс
        hashed_password = PasswordHasher.hash_password(password)

        # Создаем нового админа
        admin = AdminUser(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=hashed_password,  # Используем поле password, а не password_hash
            role=role,
            is_active=is_active
        )

        session.add(admin)
        await session.commit()

        print()
        print("✅ Администратор успешно создан!")
        print()
        print("📋 Данные для входа:")
        print(f"   Логин: {username}")
        print(f"   Email: {email}")
        print(f"   Роль: {role}")
        print(f"   Статус: {'✅ Активен' if is_active else '⏳ Не активен'}")
        print()
        if is_active:
            print("🌐 Откройте: http://localhost:8000/auth/login")
        else:
            print("⚠️  Учетная запись не активна. Обратитесь к главному администратору.")
        print()

        break


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\n\n❌ Отменено пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()