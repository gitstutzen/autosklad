"""
Бизнес-логика приёмки. Здесь и только здесь живёт то, что в desktop-версии было
размазано по FormStock.cs code-behind (раздел 11 анализа) — сознательное решение:
UI (или в вебе — фронтенд) не должен принимать решения о статусе, это забота бэкенда.

Реализация нарочно оставлена как скелет с чёткими TODO — заполняется по мере
переноса конкретных правил, каждое со ссылкой на соответствующий раздел анализа
десктоп-версии, чтобы ревьюер мог сверить логику с оригиналом.
"""
from libs.common.schemas import PositionStatus
from app.schemas import (
    PositionSearchResult, AcceptPositionRequest, AcceptPositionResponse,
    ScanMarkResponse,
)


def list_stock_tasks(stock_id: int) -> list:
    """TODO: SELECT списка StockTask по stock_id, с агрегатом
    (всего позиций / завершено позиций) — портирует загрузку списка заданий
    из FormStock при открытии (шаг 1 docs/RoboStorages_приёмка_как_это_работает.md)."""
    raise NotImplementedError


def list_positions_for_task(task_id: int) -> list:
    """TODO: SELECT всех позиций задания — объединяет 'не завершено'/'завершено'
    в один список (клиент сам решает, как группировать/сортировать), в отличие
    от desktop-версии, где это были два отдельных грида."""
    raise NotImplementedError


def parse_scan_code(raw_code: str) -> dict:
    """TODO: портировать разбор двух форматов из FormStock.tb_KeyDown:
    - формат '_' (СВОЯ_ЭТИКЕТКА): артикул_номерклиента
    - формат '-' (ПОСТАВЩИК): референс-количество
    Вернуть dict с распознанным типом и полями для поиска."""
    raise NotImplementedError


def find_position_by_scan(task_id: int, raw_code: str) -> PositionSearchResult | None:
    """TODO: SELECT по task_id + разобранному коду (parse_scan_code) в таблице positions.
    Важно: это единственное место, где обращение к БД должно происходить —
    никакой логики поиска на фронтенде (в отличие от desktop-версии, где поиск
    шёл по уже загруженной в DataGridView таблице)."""
    raise NotImplementedError


def determine_status(expected: int, accepted_total: int, has_issues: bool) -> PositionStatus:
    """Портирует расчёт статуса из FormStock.SavePosition (раздел 11 анализа).
    has_issues=True означает, что часть партии ушла в брак/недостачу/пересорт —
    даже при полном совпадении количества это ACCEPTED_WITH_ISSUES (=6), не ACCEPTED (=3)."""
    if accepted_total == 0:
        return PositionStatus.UNPROCESSED
    if accepted_total < expected:
        return PositionStatus.PARTIAL
    if accepted_total == expected:
        return PositionStatus.ACCEPTED_WITH_ISSUES if has_issues else PositionStatus.ACCEPTED
    return PositionStatus.EXCESS


def accept_position(position_id: int, body: AcceptPositionRequest, accepted_by: int) -> AcceptPositionResponse:
    """TODO:
    1. Загрузить позицию, проверить право доступа к складу этой позиции (require_stock_access).
    2. Проверить do_not_take_in_excess (аналог AppData.DoNotTakeInExcess) — если новый статус
       EXCESS и политика запрещает — вернуть 409, не сохранять.
    3. Пройти по body.outcomes, посчитать accepted_total и has_issues (см. determine_status).
    4. UPDATE позиции в транзакции (в отличие от desktop-версии, где транзакции были не везде —
       здесь оборачиваем весь accept одной транзакцией, раздел 10 анализа "несистемная
       транзакционность").
    5. Записать AuditEvent (libs.common.schemas) вместо разрозненных PositionsLogs.
    6. Если print_sticker=True — вызвать print-сервис, получить sticker_url.
    7. Если новый статус ACCEPTED/ACCEPTED_WITH_ISSUES — опубликовать событие в очередь
       для stutzen-integration (НЕ вызывать Stutzen напрямую отсюда)."""
    raise NotImplementedError


def register_scanned_mark(position_id: int, scanned_code: str, scanned_by: int) -> ScanMarkResponse:
    """TODO: сверить scanned_code (первые 22 или 31 символ) со списком непринятых
    кодов маркировки этой позиции, при совпадении — пометить как отсканированный
    и записать AuditEvent. Портирует FormStockInputMark.ProcessScannedBarcode."""
    raise NotImplementedError
