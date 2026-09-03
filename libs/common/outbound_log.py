"""
Журнал обращений к внешним системам (Stutzen, Честный Знак).

Зачем это нужно именно в этом проекте: работа идёт на боевом контуре, тестовой
базы нет. Журнал даёт возможность ответить на вопрос "это сделали мы или нет"
фактами, а не догадками — и защищает разработчика при разборе инцидента.

Пишем: что вызвали, когда, с каким результатом, сколько заняло.
НЕ пишем: значения токенов, ключей и паролей — они маскируются перед записью.
"""
import logging
import re
import time
from contextlib import contextmanager

logger = logging.getLogger("outbound")

# Параметры и заголовки, значения которых никогда не должны попасть в лог.
SECRET_KEYS = {"token", "apikey", "api_key", "x-api-key", "password", "authorization"}

_SECRET_IN_URL = re.compile(r"([?&](?:token|apikey|api_key)=)([^&\s]+)", re.IGNORECASE)


def redact_url(url: str) -> str:
    """Убирает значения секретов из строки URL перед записью в лог.
    Токен TradeSoft передаётся GET-параметром, поэтому иначе он попал бы
    в каждую строчку журнала."""
    return _SECRET_IN_URL.sub(r"\1***", str(url))


def redact_mapping(data: dict | None) -> dict:
    """То же самое для словарей параметров и заголовков."""
    if not data:
        return {}
    return {
        k: ("***" if k.lower() in SECRET_KEYS else v)
        for k, v in data.items()
    }


@contextmanager
def log_outbound(system: str, operation: str, url: str, read_only: bool, **context):
    """Оборачивает один исходящий вызов.

    system    — куда идём ("tradesoft", "api1c", "crpt")
    operation — что делаем ("GET order-positions", "set_position_status")
    read_only — был ли включён режим только чтения в момент вызова
    context   — дополнительные поля (id позиции, фильтры и т.п.), уже без секретов
    """
    started = time.monotonic()
    safe_url = redact_url(url)
    logger.info(
        "outbound.start system=%s op=%s url=%s read_only=%s ctx=%s",
        system, operation, safe_url, read_only, context,
    )
    try:
        yield
    except Exception as exc:
        elapsed = (time.monotonic() - started) * 1000
        logger.error(
            "outbound.error system=%s op=%s url=%s elapsed_ms=%.0f error=%s",
            system, operation, safe_url, elapsed, type(exc).__name__,
        )
        raise
    else:
        elapsed = (time.monotonic() - started) * 1000
        logger.info(
            "outbound.ok system=%s op=%s url=%s elapsed_ms=%.0f",
            system, operation, safe_url, elapsed,
        )
