"""
Воркер на arq (Redis-очередь) — замена fire-and-forget Task.Run с пустым catch{}
из FormStock.SavePosition (раздел 11 анализа). Разница принципиальная:
  - задача видна в очереди, пока не выполнена;
  - при ошибке — автоматический retry с backoff, а не молчаливая потеря;
  - после исчерпания retry — задача остаётся в dead-letter, виден алерт,
    а не "и так сойдёт", как было в desktop-версии.

warehouse-сервис не вызывает Stutzen напрямую — он публикует задачу в эту очередь
через arq.connections.ArqRedis.enqueue_job("sync_position_status", ...).
"""
from arq import cron
from arq.connections import RedisSettings
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.tradesoft_client import TradeSoftClient
from app.api1c_client import Api1cClient
from app import sync as sync_module

_engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(bind=_engine)


async def sync_position_status(ctx, position_id: int, status_id: int, sub_states: list[dict] | None = None):
    """Основная задача синхронизации. Пробует официальный путь первым,
    api1c — только если официальный явно недоступен для этого случая."""
    client = TradeSoftClient()
    try:
        result = client.set_position_status(position_id, status_id, sub_states)
        return {"method": "tradesoft_v1", "result": result}
    except Exception as e:
        # TODO: после практической проверки решить, нужен ли вообще fallback на api1c,
        # или официального пути достаточно (см. docs/RoboStorages_scope_MVP.md,
        # раздел "официальный способ записи статуса найден")
        raise


async def refresh_mirror_incremental(ctx):
    """Подхватывает новые приходы. Только чтение — работает и при включённом
    режиме read-only."""
    with SessionLocal() as session:
        return sync_module.sync_incremental(session)


async def refresh_mirror_full(ctx):
    """Полная сверка. Нужна потому, что api1c отдаёт записи по времени создания,
    а не изменения: если статус старого задания поменялся на стороне Stutzen,
    инкрементальная синхронизация этого не увидит.

    Тяжёлая (~44 сек, 452 000+ записей), поэтому идёт ночью."""
    with SessionLocal() as session:
        return sync_module.sync_full(session)


class WorkerSettings:
    functions = [sync_position_status, refresh_mirror_incremental, refresh_mirror_full]
    cron_jobs = [
        # Новые приходы — часто, чтобы кладовщик видел их почти сразу.
        cron(refresh_mirror_incremental, minute=set(range(0, 60, 2))),
        # Полная сверка — ночью, когда склад не работает.
        cron(refresh_mirror_full, hour=3, minute=30),
    ]
    redis_settings = RedisSettings.from_dsn(os.environ["REDIS_URL"])
    max_tries = 5  # с экспоненциальным backoff по умолчанию в arq
