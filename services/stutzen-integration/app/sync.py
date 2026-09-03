"""
Синхронизация зеркала складских заданий с api1c.

Два режима, и оба нужны:

  ИНКРЕМЕНТАЛЬНАЯ (часто, раз в минуту-две)
      Забирает последние N записей. Ловит новые приходы почти сразу.
      Быстро: 5000 записей отдаются за ~0.55 сек.

  ПОЛНАЯ (редко, раз в сутки в нерабочее время)
      Забирает всю историю (452 000+ записей, ~44 сек).

Почему нельзя обойтись одной инкрементальной: api1c отдаёт записи по убыванию id,
то есть в порядке СОЗДАНИЯ, а не изменения. Если у задания трёхнедельной давности
поменяется статус, оно не всплывёт в свежем срезе, и инкрементальная синхронизация
этого не заметит. Полная сверка раз в сутки закрывает этот пробел.

Дополнительная страховка: при открытии конкретного задания кладовщиком его данные
запрашиваются из api1c напрямую, поэтому расхождение зеркала не приводит к работе
по устаревшим сведениям в момент приёмки.
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.api1c_client import Api1cClient
from app.models import StockTaskMirror, SyncState
from app.stock_tasks import StockTask, parse_stock_tasks_detailed

logger = logging.getLogger("sync")

# Размер порции для инкрементальной синхронизации. 5000 покрывает несколько суток
# при текущем темпе (~800-900 новых приходов в сутки) — с большим запасом
# на случай, если синхронизация не отрабатывала несколько часов.
INCREMENTAL_COUNT = 5000

# Сколько строк отправлять в базу за один раз при полной выгрузке.
# Вставлять 452 000 строк одним запросом нельзя — не хватит памяти и превысим
# лимиты драйвера.
UPSERT_BATCH_SIZE = 1000


def _to_row(task: StockTask, now: datetime) -> dict:
    return {
        "id": task.id,
        "receipt_number": task.receipt_number,
        "document_number": task.document_number,
        "created_at": task.created_at,
        "changed_at": task.changed_at,
        "status": task.status,
        "stock_id": task.stock_id,
        "provider": task.provider,
        # Нормализованная копия для поиска без учёта регистра.
        # Приводим регистр здесь, в Python, а не запросом в базе —
        # см. комментарий у StockTaskMirror.provider_search.
        "provider_search": (task.provider or "").lower(),
        "amount": task.amount,
        "login": task.login,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "comment": task.comment,
        "comment_stock": task.comment_stock,
        "synced_at": now,
    }


def upsert_tasks(session: Session, tasks: list[StockTask]) -> int:
    """Вставляет новые записи и обновляет существующие.

    Обновление по ключу id: если задание уже есть, перезаписываем поля значениями
    из источника. Зеркало не хранит собственных данных, поэтому затирать нечего.
    """
    if not tasks:
        return 0

    now = datetime.utcnow()
    processed = 0

    for start in range(0, len(tasks), UPSERT_BATCH_SIZE):
        batch = tasks[start:start + UPSERT_BATCH_SIZE]
        rows = [_to_row(t, now) for t in batch]

        stmt = pg_insert(StockTaskMirror).values(rows)
        update_columns = {
            c.name: stmt.excluded[c.name]
            for c in StockTaskMirror.__table__.columns
            if c.name != "id"
        }
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_columns)

        session.execute(stmt)
        processed += len(batch)

    session.commit()
    return processed


def _record_state(session: Session, name: str, rows: int, error: str | None = None) -> None:
    state = session.get(SyncState, name) or SyncState(name=name)
    if error is None:
        state.last_success_at = datetime.utcnow()
        state.last_error = None
        state.rows_processed = rows
    else:
        state.last_error = error[:2000]
    session.merge(state)
    session.commit()


def sync_incremental(session: Session, count: int = INCREMENTAL_COUNT) -> int:
    """Подхватывает свежие приходы. Запускать часто."""
    try:
        payload = Api1cClient().get_stock_tasks(count=count)
        parsed = parse_stock_tasks_detailed(payload) if isinstance(payload, list) else None
        if parsed is None:
            raise ValueError("api1c вернул не список")
        if parsed.skipped:
            logger.error("sync.incremental: %s", parsed.report())
        rows = upsert_tasks(session, parsed.tasks)
        _record_state(session, "incremental", rows)
        logger.info("sync.incremental ok rows=%s", rows)
        return rows
    except Exception as exc:
        _record_state(session, "incremental", 0, f"{type(exc).__name__}: {exc}")
        logger.error("sync.incremental failed: %s", type(exc).__name__)
        raise


def sync_full(session: Session) -> int:
    """Полная сверка со всей историей. Запускать раз в сутки в нерабочее время.

    Нужна потому, что изменения в СТАРЫХ заданиях (например, приход
    трёхнедельной давности наконец закрыли) не попадают в свежий срез:
    api1c сортирует по id, то есть по времени создания, а не изменения.
    """
    try:
        # Без count api1c отдаёт всю историю. Это тяжёлый запрос (~44 сек),
        # поэтому вызывается только отсюда и только по расписанию.
        payload = Api1cClient().get_stock_tasks()
        if not isinstance(payload, list):
            raise ValueError(f"api1c вернул не список, а {type(payload).__name__}")

        parsed = parse_stock_tasks_detailed(payload)
        if parsed.skipped:
            # Не молчим: потеря записей при полной сверке означает, что зеркало
            # неполное, и кладовщик не увидит часть приходов.
            logger.error(
                "sync.full: получено %s записей, %s",
                len(payload), parsed.report(),
            )
        else:
            logger.info("sync.full: получено %s записей, все разобраны", len(payload))

        rows = upsert_tasks(session, parsed.tasks)
        _record_state(session, "full", rows)
        logger.info("sync.full ok rows=%s", rows)
        return rows
    except Exception as exc:
        _record_state(session, "full", 0, f"{type(exc).__name__}: {exc}")
        logger.error("sync.full failed: %s", type(exc).__name__)
        raise


def get_sync_status(session: Session) -> dict:
    """Состояние синхронизаций — для эндпоинта /health и для диагностики.

    Если инкрементальная давно не отрабатывала, кладовщик может не увидеть
    новый приход, и об этом лучше знать заранее, а не по жалобе со склада.
    """
    states = session.execute(select(SyncState)).scalars().all()
    return {
        s.name: {
            "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
            "rows_processed": s.rows_processed,
            "last_error": s.last_error,
        }
        for s in states
    }
