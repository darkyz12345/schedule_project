import bcrypt
from typing import Optional


class PasswordHasher:
    """Безопасное хэширование и проверка паролей"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Хэширует пароль с помощью bcrypt
        :param password:  Пароль в виде строки
        :return: Хэшированный пароль в виде строки
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля хэшу
        :param password: Пароль для проверки
        :param hashed_password: Хэшированный пароль
        :return: Если пароль верный - True, иначе - False
        """
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)