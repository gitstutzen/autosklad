from pydantic import BaseModel, Field

# Импорт из общей библиотеки — единственный источник истины для статусов позиции,
# см. libs/common/schemas.py::PositionStatus.
from libs.common.schemas import PositionStatus


class PositionSearchResult(BaseModel):
    """Ответ на поиск позиции по скану — заменяет поиск по in-memory таблице
    из FormStock.tb_KeyDown (раздел "как работает приёмка"). Здесь это обычный
    серверный запрос: клиент отправляет отсканированный код, сервер ищет в БД,
    а не в загруженном в браузер списке всего задания."""
    position_id: int
    article: str
    manufacturer: str
    price: float
    quantity_expected: int
    quantity_already_accepted: int
    requires_marking: bool
    client_ref: str | None = None
    trade_point_short_name: str | None = None


class AcceptOutcome(BaseModel):
    """Один из исходов приёмки партии: часть чисто, часть — брак/недостача/пересорт.
    Соответствует полю subStates из api/v1/order-positions TradeSoft — тот же принцип
    "расщепления" одной позиции на несколько исходов одним запросом."""
    quantity: int = Field(gt=0)
    outcome: PositionStatus


class AcceptPositionRequest(BaseModel):
    """POST /warehouse/positions/{id}/accept — замена FormStock.SavePosition.
    В отличие от desktop-версии, ничего не берётся из глобального контекста
    (AppPosition/AppData) — всё приходит явно в теле запроса."""
    outcomes: list[AcceptOutcome]
    comment: str | None = None
    print_sticker: bool = True


class AcceptPositionResponse(BaseModel):
    position_id: int
    new_status: PositionStatus
    sticker_url: str | None = None  # если print_sticker=True — ссылка на PDF от print-сервиса


class ScanMarkRequest(BaseModel):
    """POST /warehouse/positions/{id}/scan-mark — замена FormStockInputMark.ProcessScannedBarcode.
    Здесь только сверка со списком кодов, ожидаемых для этой позиции;
    сверка с государственным реестром — отдельный вызов marking-сервиса, не здесь."""
    scanned_code: str


class ScanMarkResponse(BaseModel):
    matched: bool
    remaining_count: int
    all_scanned: bool
