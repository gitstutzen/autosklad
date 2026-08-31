"""
Общие Pydantic-схемы, которыми пользуются несколько сервисов.
Держим здесь только то, что реально пересекает границы сервисов (контракты между ними) —
внутренние модели каждого сервиса живут в его собственном app/schemas.py.
"""
from datetime import datetime
from enum import IntEnum
from pydantic import BaseModel


class PositionStatus(IntEnum):
    """Статус позиции при приёмке (PositionsStorage.StatusPosition в desktop-версии).

    Найдено построчным разбором FormStock.SavePosition (раздел 11 анализа).
    Значение 6 отсутствовало в исходном справочнике LocalDb и было обнаружено
    только при разборе кода — держим как единственный источник истины теперь.
    """
    UNPROCESSED = 1     # Необработана
    PARTIAL = 2         # Частично
    ACCEPTED = 3        # Принята (чисто, без замечаний)
    EXCESS = 4          # Излишек
    MISSING = 5         # Отсутствует
    ACCEPTED_WITH_ISSUES = 6  # Принята, но есть брак/недостача/пересорт


class CurrentUser(BaseModel):
    """Результат проверки JWT — то, что auth-сервис кладёт в токен,
    а остальные сервисы читают через libs/common/auth_middleware.py."""
    user_id: int
    login: str
    allowed_stock_ids: list[int]
    allowed_provider_ids: list[int] | None = None


class ServiceError(BaseModel):
    """Единый формат ошибки на всех сервисах — фронтенду не нужно знать,
    какой сервис ответил, формат один и тот же."""
    error_code: str
    message: str
    details: dict | None = None


class AuditEvent(BaseModel):
    """Общий формат события для аудит-лога (замена разрозненных
    PositionsLogs / PositionsStatusLog / UserLog из desktop-версии)."""
    occurred_at: datetime
    user_id: int
    entity_type: str
    entity_id: int
    action: str
    payload: dict | None = None
