from fastapi import APIRouter
from pydantic import BaseModel

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser
from fastapi import Depends
from app.worker import sync_position_status  # noqa: F401  (используется через arq enqueue, не напрямую)
from app.api1c_client import Api1cClient

router = APIRouter()


class SyncStatusRequest(BaseModel):
    position_id: int
    status_id: int
    sub_states: list[dict] | None = None


@router.post("/positions/{position_id}/sync-status")
async def sync_status(position_id: int, body: SyncStatusRequest, user: CurrentUser = Depends(require_user)):
    """Вызывается warehouse-сервисом (не напрямую фронтендом) после успешной приёмки.
    Реально ничего не делает синхронно — только кладёт задачу в очередь (см. app/worker.py),
    чтобы сбой синхронизации со Stutzen не блокировал ответ кладовщику и не терялся молча,
    как это было в desktop-версии (раздел 11 анализа, fire-and-forget с пустым catch{})."""
    from arq import create_pool
    from arq.connections import RedisSettings
    import os

    redis = await create_pool(RedisSettings.from_dsn(os.environ["REDIS_URL"]))
    job = await redis.enqueue_job(
        "sync_position_status", body.position_id, body.status_id, body.sub_states
    )
    return {"queued": True, "job_id": job.job_id}


@router.get("/order-states")
def get_order_states():
    """Справочник статусов с человекочитаемыми названиями — из api1c/Warehouse/GetOrderStates,
    заменяет захардкоженный в desktop-версии список из 93 значений (раздел 11 анализа).
    Кэшируется на уровне gateway/фронтенда — справочник меняется редко."""
    return Api1cClient().get_order_states()
