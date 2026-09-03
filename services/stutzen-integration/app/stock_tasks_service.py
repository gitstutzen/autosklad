"""
Запросы к списку складских заданий.

Читаем из локального зеркала (app/models.py), а не из api1c напрямую. Причины
подробно описаны в app/sync.py, если коротко: у api1c нет фильтров, нет
постраничности и нет выборки по номеру, а полная выгрузка занимает ~44 секунды.

Главное практическое следствие для склада: задание, по которому часть позиций
не приняли (например, поставка задержалась), остаётся доступным сколько угодно
долго — оно просто лежит в нашей базе со статусом "не завершено", и кладовщик
может вернуться к нему через неделю или через месяц.
"""
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StockTaskMirror
from app.stock_tasks import ACTIVE_STATUSES

# Задание считается активным (требующим работы кладовщика) при статусах 1, 2, 5, 6.
# Статусы 3 и 4 — завершённые.
#
# Разделение взято из SQL-запросов десктоп-версии (FormStock.cs): вкладка
# "не завершено" запрашивает статусы 1, 2, 5, 6, вкладка "завершено" — 3 и 4.
#
# Раньше здесь было условие "статус != 4", и это была ошибка: в статусе 3
# в боевых данных висит 8654 задания, включая записи 2017 года. Они попадали бы
# в список кладовщика как активные, хотя давно закрыты.
ACTIVE_STATUS_VALUES = [int(s) for s in ACTIVE_STATUSES]


def list_tasks(
    session: Session,
    stock_id: int | None = None,
    only_unfinished: bool = True,
    provider_contains: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StockTaskMirror]:
    """Список заданий с фильтрами.

    Все эти фильтры api1c не поддерживает — они возможны только потому,
    что данные лежат у нас.
    """
    query = select(StockTaskMirror)

    if stock_id is not None:
        query = query.where(StockTaskMirror.stock_id == stock_id)

    if only_unfinished:
        query = query.where(StockTaskMirror.status.in_(ACTIVE_STATUS_VALUES))

    if provider_contains:
        # Сравниваем нормализованное поле с нормализованным запросом — так поиск
        # работает одинаково в SQLite и PostgreSQL. Подробности в модели,
        # поле StockTaskMirror.provider_search.
        query = query.where(
            StockTaskMirror.provider_search.contains(provider_contains.lower())
        )

    if created_from:
        query = query.where(
            StockTaskMirror.created_at >= datetime.combine(created_from, time.min)
        )

    if created_to:
        query = query.where(
            StockTaskMirror.created_at <= datetime.combine(created_to, time.max)
        )

    # Свежие сверху — кладовщик чаще всего работает с сегодняшними приходами,
    # но старые незакрытые остаются доступны прокруткой и фильтрами.
    query = query.order_by(StockTaskMirror.created_at.desc())
    query = query.limit(limit).offset(offset)

    return list(session.execute(query).scalars().all())


def get_task(session: Session, task_id: int) -> StockTaskMirror | None:
    """Одно задание по номеру. В api1c такой возможности нет вообще —
    работает только благодаря зеркалу."""
    return session.get(StockTaskMirror, task_id)


def count_unfinished(session: Session, stock_id: int) -> int:
    """Сколько незакрытых заданий на складе. Полезно для сводки на экране:
    сюда попадают и старые приходы с неполученными позициями."""
    query = select(StockTaskMirror).where(
        StockTaskMirror.stock_id == stock_id,
        StockTaskMirror.status.in_(ACTIVE_STATUS_VALUES),
    )
    return len(list(session.execute(query).scalars().all()))
