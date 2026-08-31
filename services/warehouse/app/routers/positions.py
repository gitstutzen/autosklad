from fastapi import APIRouter, Depends, HTTPException

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser, PositionStatus
from app.schemas import (
    PositionSearchResult,
    AcceptPositionRequest,
    AcceptPositionResponse,
    ScanMarkRequest,
    ScanMarkResponse,
)
from app import service

router = APIRouter()


@router.get("/search", response_model=PositionSearchResult)
def search_position(code: str, task_id: int, user: CurrentUser = Depends(require_user)):
    """Поиск позиции по отсканированному коду внутри задания.
    Заменяет два формата разбора скана из FormStock.tb_KeyDown ('_' — своя этикетка,
    '-' — референс поставщика) — оба формата обрабатываются в service.parse_scan_code,
    но поиск совпадения теперь идёт в БД, а не в загруженной в браузер таблице."""
    result = service.find_position_by_scan(task_id=task_id, raw_code=code)
    if result is None:
        raise HTTPException(404, "Позиция по этому коду не найдена в задании")
    return result


@router.post("/{position_id}/accept", response_model=AcceptPositionResponse)
def accept_position(
    position_id: int,
    body: AcceptPositionRequest,
    user: CurrentUser = Depends(require_user),
):
    """Принять позицию (полностью или частично, с исходами брак/недостача/пересорт).

    Логика статуса 1:1 портирует FormStock.SavePosition (раздел 11 анализа):
      quantity == 0            -> UNPROCESSED
      quantity < expected       -> PARTIAL
      quantity == expected, ok  -> ACCEPTED
      quantity == expected, issues -> ACCEPTED_WITH_ISSUES
      quantity > expected       -> EXCESS (блокируется, если у пользователя/склада
                                   включена политика do_not_take_in_excess)

    В отличие от desktop-версии, синхронизация статуса со Stutzen НЕ идёт synchronously
    и не глотает ошибки в пустом catch{} — здесь она публикуется в очередь
    (см. stutzen-integration/app/worker.py) и обрабатывается асинхронно с ретраями.
    """
    return service.accept_position(position_id, body, accepted_by=user.user_id)


@router.post("/{position_id}/scan-mark", response_model=ScanMarkResponse)
def scan_mark(
    position_id: int,
    body: ScanMarkRequest,
    user: CurrentUser = Depends(require_user),
):
    """Сканирование одного кода маркировки для позиции — портирует
    FormStockInputMark.ProcessScannedBarcode. Сверяет первые 22 или 31 символ
    кода (два формата кода Честного Знака) со списком ожидаемых кодов позиции."""
    return service.register_scanned_mark(position_id, body.scanned_code, scanned_by=user.user_id)
