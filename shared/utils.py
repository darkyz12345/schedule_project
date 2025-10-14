"""
Общие утилиты, используемые и в боте, и в веб-сервисе
"""
import time
from typing import Any
from functools import wraps

from config.logger import get_logger
from structlog.contextvars import bind_contextvars


# ============ ДЕКОРАТОРЫ ============

def log_execution(service: str = None):
    """
    Декоратор для логирования выполнения функций

    Args:
        service: Название сервиса (bot/web), если None - берется из контекста

    Example:
        @log_execution(service="bot")
        async def process_payment(user_id: int):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__, service=service)

            logger.debug(
                "function_started",
                function=func.__name__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.debug(
                    "function_completed",
                    function=func.__name__,
                    duration_ms=round(duration * 1000, 2),
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    duration_ms=round(duration * 1000, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__, service=service)

            logger.debug(
                "function_started",
                function=func.__name__,
            )

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.debug(
                    "function_completed",
                    function=func.__name__,
                    duration_ms=round(duration * 1000, 2),
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    duration_ms=round(duration * 1000, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise

        # Возвращаем правильную обертку
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============ КЛАССЫ ДЛЯ РАБОТЫ С ВНЕШНИМИ СЕРВИСАМИ ============

class DatabaseLogger:
    """Логирование операций с базой данных"""

    def __init__(self, service: str = None):
        self.logger = get_logger("database", service=service)

    async def log_query(
            self,
            operation: str,
            table: str,
            duration_ms: float = None,
            rows_affected: int = None,
            **kwargs: Any
    ) -> None:
        """Логировать SQL запрос"""
        log_data = {
            "operation": operation,
            "table": table,
            **kwargs,
        }

        if duration_ms is not None:
            log_data["duration_ms"] = round(duration_ms, 2)

        if rows_affected is not None:
            log_data["rows_affected"] = rows_affected

        self.logger.info("db_query", **log_data)

    async def log_error(
            self,
            operation: str,
            table: str,
            error: Exception,
            **kwargs: Any
    ) -> None:
        """Логировать ошибку БД"""
        self.logger.error(
            "db_error",
            operation=operation,
            table=table,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
            **kwargs,
        )


class ExternalAPILogger:
    """Логирование вызовов внешних API"""

    def __init__(self, api_name: str, service: str = None):
        self.api_name = api_name
        self.logger = get_logger(f"external_api.{api_name}", service=service)

    def log_request(
            self,
            method: str,
            endpoint: str,
            **kwargs: Any
    ) -> None:
        """Логировать начало запроса"""
        self.logger.info(
            "api_request_started",
            api=self.api_name,
            method=method,
            endpoint=endpoint,
            **kwargs,
        )

    def log_response(
            self,
            method: str,
            endpoint: str,
            status_code: int,
            duration_ms: float,
            **kwargs: Any
    ) -> None:
        """Логировать успешный ответ"""
        self.logger.info(
            "api_response_received",
            api=self.api_name,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )

    def log_error(
            self,
            method: str,
            endpoint: str,
            error: Exception,
            **kwargs: Any
    ) -> None:
        """Логировать ошибку"""
        self.logger.error(
            "api_request_failed",
            api=self.api_name,
            method=method,
            endpoint=endpoint,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
            **kwargs,
        )


# ============ ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ============

# Для работы с БД (используется и в боте, и в веб)
db_logger = DatabaseLogger()


@log_execution()
async def get_user_from_db(user_id: int) -> dict:
    """Пример функции работы с БД"""
    start_time = time.time()

    try:
        # Имитация запроса к БД
        # result = await db.users.find_one({"id": user_id})
        result = {"id": user_id, "name": "John"}

        duration = (time.time() - start_time) * 1000
        await db_logger.log_query(
            operation="SELECT",
            table="users",
            duration_ms=duration,
            rows_affected=1,
            user_id=user_id,
        )

        return result

    except Exception as e:
        await db_logger.log_error(
            operation="SELECT",
            table="users",
            error=e,
            user_id=user_id,
        )
        raise


# Для работы с внешними API
payment_api_logger = ExternalAPILogger("payment_gateway")


async def process_payment(user_id: int, amount: float) -> bool:
    """Пример обработки платежа с логированием"""
    endpoint = "/v1/payments"
    start_time = time.time()

    try:
        payment_api_logger.log_request(
            method="POST",
            endpoint=endpoint,
            user_id=user_id,
            amount=amount,
        )

        # Имитация запроса к платежному API
        # response = await payment_api.charge(...)

        duration = (time.time() - start_time) * 1000
        payment_api_logger.log_response(
            method="POST",
            endpoint=endpoint,
            status_code=200,
            duration_ms=duration,
            user_id=user_id,
        )

        return True

    except Exception as e:
        payment_api_logger.log_error(
            method="POST",
            endpoint=endpoint,
            error=e,
            user_id=user_id,
            amount=amount,
        )
        raise


# ============ КОНТЕКСТНЫЕ МЕНЕДЖЕРЫ ============

class LogContext:
    """Контекстный менеджер для добавления временного контекста в логи"""

    def __init__(self, **context: Any):
        self.context = context
        self.previous_context = {}

    def __enter__(self):
        bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Контекст автоматически очистится при выходе из scope
        pass

# Пример использования:
# with LogContext(operation="payment", payment_id=123):
#     logger.info("processing_payment")  # Автоматически добавит operation и payment_id