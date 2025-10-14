"""
Общие middleware для бота и веб-сервиса
"""
import time
import uuid
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


# ============ MIDDLEWARE ДЛЯ БОТА ============

class BotLoggingMiddleware(BaseMiddleware):
    """Middleware для логирования событий бота"""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> Any:
        clear_contextvars()

        request_id = str(uuid.uuid4())[:8]
        logger = structlog.get_logger()

        # Извлекаем информацию
        user_id = None
        username = None
        chat_id = None
        event_type = type(event).__name__

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            username = event.from_user.username if event.from_user else None
            chat_id = event.chat.id if event.chat else None
            event_info = {
                "message_id": event.message_id,
                "text": event.text[:100] if event.text else None,
                "content_type": event.content_type,
            }
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            username = event.from_user.username if event.from_user else None
            chat_id = event.message.chat.id if event.message and event.message.chat else None
            event_info = {
                "callback_data": event.data,
                "message_id": event.message.message_id if event.message else None,
            }
        else:
            event_info = {}

        # Привязываем контекст
        bind_contextvars(
            service="bot",
            request_id=request_id,
            user_id=user_id,
            username=username,
            chat_id=chat_id,
            event_type=event_type,
        )

        logger.info("bot_event_received", **event_info)

        start_time = time.time()

        try:
            result = await handler(event, data)

            duration = time.time() - start_time
            logger.info(
                "bot_event_processed",
                duration_ms=round(duration * 1000, 2),
                success=True,
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "bot_event_failed",
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
        finally:
            clear_contextvars()


# ============ MIDDLEWARE ДЛЯ ВЕБА ============

class WebLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования HTTP запросов"""

    async def dispatch(
            self,
            request: Request,
            call_next: Callable,
    ) -> Response:
        clear_contextvars()

        request_id = str(uuid.uuid4())[:8]
        logger = structlog.get_logger()

        # Извлекаем информацию о запросе
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent", "unknown")

        # Привязываем контекст
        bind_contextvars(
            service="web",
            request_id=request_id,
            client_ip=client_ip,
            method=method,
            path=path,
            user_agent=user_agent,
        )

        logger.debug(
            "web_request_received",
            query_params=dict(request.query_params) if request.query_params else None,
        )

        start_time = time.time()

        try:
            response = await call_next(request)

            duration = time.time() - start_time

            # Добавляем request_id в заголовки
            response.headers["X-Request-ID"] = request_id

            logger.info(
                "web_request_completed",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "web_request_failed",
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
        finally:
            clear_contextvars()


# ============ ОБЩИЙ MIDDLEWARE ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ ============

class PerformanceMiddleware:
    """Универсальный middleware для отслеживания медленных операций"""

    def __init__(self, threshold_ms: float = 1000):
        self.threshold_ms = threshold_ms

    def log_if_slow(self, operation: str, duration_ms: float, **context: Any):
        """Логировать, если операция медленная"""
        if duration_ms > self.threshold_ms:
            logger = structlog.get_logger("performance")
            logger.warning(
                "slow_operation_detected",
                operation=operation,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.threshold_ms,
                **context,
            )


# Глобальный экземпляр для использования в обоих сервисах
performance_monitor = PerformanceMiddleware(threshold_ms=1000)