from fastapi import APIRouter, Depends, HTTPException

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser
from app import service
from app.schemas import PositionSearchResult
from pydantic import BaseModel

router = APIRouter()


class StockTaskSummary(BaseModel):
    """Одна строка списка заданий — то, что кладовщик видит при открытии
    RoboStorages (шаг 1 в docs/RoboStorages_приёмка_как_это_работает.md)."""
    task_id: int
    provider_name: str
    created_at: str
    positions_total: int
    positions_completed: int


@router.get("", response_model=list[StockTaskSummary])
def list_tasks(stock_id: int, user: CurrentUser = Depends(require_user)):
    """Список заданий на приёмку для конкретного склада — открывающий экран.
    Доступ проверяется по allowed_stock_ids из токена (замена SetStocksRight,
    раздел 9 анализа), а не по глобальному AppData.StockId, как в desktop-версии."""
    if stock_id not in user.allowed_stock_ids:
        raise HTTPException(403, "Нет доступа к этому складу")
    return service.list_stock_tasks(stock_id)


@router.get("/{task_id}/positions", response_model=list[PositionSearchResult])
def list_task_positions(task_id: int, user: CurrentUser = Depends(require_user)):
    """Все позиции задания — заменяет одновременную загрузку двух гридов
    ('не завершено' / 'завершено') из FormStock. В отличие от desktop-версии,
    порядок и статус клиент запрашивает у сервера при каждом открытии,
    а не держит в памяти локальную копию, которая может разойтись с базой."""
    return service.list_positions_for_task(task_id)
