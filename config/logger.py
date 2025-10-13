import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor

LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)
_logger_initialized = False


def add_service_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict.pop('color_message', None)
    return event_dict


class ServiceFilter(logging.Filter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        service = getattr(record, 'service', None)
        return service == self.service or service is None


def setup_logger(
        log_level: str = "INFO",
        json_logs: bool = False,
        enable_console: bool = True
) -> None:
    global _logger_initialized
    if _logger_initialized:
        return
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        add_service_context,
        timestamper
    ]
    if json_logs:
        structlog_processors = shared_processors + [
            drop_color_message_key,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer()
            ]
        )
    else:
        structlog_processors = shared_processors + [
            structlog.dev.set_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=False)
            ]
        )
    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True
    )
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if log_level == "DEBUG" else logging.INFO)
        if not json_logs:
            console_formatter = structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared_processors,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=True)
                ]
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    all_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'app.log',
        maxBytes=20 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    all_handler.setLevel(logging.DEBUG)
    all_handler.setFormatter(formatter)
    root_logger.addHandler(all_handler)

    bot_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'bot.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    bot_handler.setLevel(logging.DEBUG)
    bot_handler.setFormatter(formatter)
    bot_handler.addFilter(ServiceFilter("bot"))
    root_logger.addHandler(bot_handler)

    web_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'web.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    web_handler.setLevel(logging.DEBUG)
    web_handler.setFormatter(formatter)
    web_handler.addFilter(ServiceFilter("web"))
    root_logger.addHandler(web_handler)

    error_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / 'error.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.DEBUG)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    audit_logger = logging.getLogger('audit')
    audit_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'audit.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding='utf-8'
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(formatter)
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    logging.getLogger('aiogram').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.INFO)

    _logger_initialized = True
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logger_initialized",
        log_level=log_level,
        json_logs=json_logs,
        log_dir=str(LOG_DIR.absolute())
    )


def get_logger(
        name: str | None = None,
        service: str | None = None,
        **context: Any
) -> structlog.stdlib.BoundLogger:
    """
    Получить логгер с привязанным контекстом

    Args:
        name: Имя логгера (обычно name)
        service: Сервис (bot, web)
        **context: Дополнительный контекст для привязки

    Returns:
        Настроенный structlog логгер

    Example:
    logger = get_logger(name, service="bot", user_id=123)
        logger.info("user_action", action="start")
    """
    logger = structlog.get_logger(name)

    # Привязываем контекст сервиса
    bind_context = {}
    if service:
        bind_context["service"] = service
    if context:
        bind_context.update(context)

    if bind_context:
        logger = logger.bind(**bind_context)

    return logger


def get_audit_logger(**context: Any) -> structlog.stdlib.BoundLogger:
    """
    Получить логгер для аудита

    Example:
        audit = get_audit_logger(user_id=123)
        audit.info("user_registered", email="user@example.com")
    """
    logger = structlog.get_logger("audit")
    if context:
        logger = logger.bind(**context)
    return logger
