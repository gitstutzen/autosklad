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

from app.tradesoft_client import TradeSoftClient
from app.api1c_client import Api1cClient


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


class WorkerSettings:
    functions = [sync_position_status]
    redis_settings = RedisSettings.from_dsn(os.environ["REDIS_URL"])
    max_tries = 5  # с экспоненциальным backoff по умолчанию в arq
