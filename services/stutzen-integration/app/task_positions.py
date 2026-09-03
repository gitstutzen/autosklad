"""
Разбор ответа api1c/RoboStorage/GetStockTaskPositions — позиции внутри задания.

Структура описана по РЕАЛЬНОМУ ответу боевого API (пробник от 02.09.2026).

ВАЖНО про параметр запроса: метод принимает `dcc_id`, и значение туда идёт
из поля `documentNumber` ЗАДАНИЯ, а не из его `id` и не из `stk_id`.
Проверено перебором: 7 имён параметров × 3 значения, сработало одно сочетание.
Подтверждается SQL десктоп-версии: PositionsStorage.dcc_id = StockTasks.DocumentNumber.

Цена ошибки здесь высокая: при неверном параметре API отвечает 200 OK и пустым
списком — без ошибки. Экран просто окажется пустым, и причину будет не видно.
"""
from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, field_validator

from app.stock_tasks import DOTNET_EMPTY_DATE


class PositionStatus(IntEnum):
    """Статус позиции при приёмке (PositionsStorage.StatusPosition).

    Названия сверены со справочной таблицей PositionsStorageStatus боевой базы
    (прочитано напрямую 02.09.2026) — все шесть значений подтвердились.
    Не путать со статусом ЗАДАНИЯ (StockTaskStatus) — это разные шкалы.
    """
    UNPROCESSED = 1           # Необработана
    PARTIAL = 2               # Принята частично
    ACCEPTED = 3              # Принята
    EXCESS = 4                # Излишек
    MISSING = 5               # Отсутствует
    ACCEPTED_WITH_ISSUES = 6  # Принято с разногласием


class TaskPosition(BaseModel):
    """Одна строка накладной внутри задания."""

    article: str                       # article — артикул детали
    article_new: str | None = None     # articleNew — артикул замены, если была
    manufacturer: str                  # manufacturer
    name: str                          # name — наименование детали
    quantity: int                      # quantity — ожидается по накладной
    quantity_fact: int                 # quantityFact — принято фактически
    quantity_scanned: int              # quantityScanned
    quantity_total_scanned: int        # quantityTotalScanned
    price: float                       # price — цена за штуку
    price_total: float                 # priceTotal — сумма по позиции
    ref_stutzen: int                   # refStutzen — ссылка для поиска по скану
    ref_provider: int                  # refProvider — ссылка поставщика
    trade_point: int                   # tradePoint — точка назначения (на этикетку)
    number_customer: int               # numberCustomer — клиент (на этикетку)
    status_position: int               # statusPosition — см. PositionStatus
    comment: str | None = None         # comment
    processing_started_at: datetime | None = None    # processingStartTime
    processing_finished_at: datetime | None = None   # processingCompletionTime
    changed_at: datetime | None = None               # timeOfLastChange

    @field_validator(
        "processing_started_at", "processing_finished_at", "changed_at", mode="before"
    )
    @classmethod
    def empty_dotnet_date_to_none(cls, value):
        """0001-01-01T00:00:00 у .NET означает «не заполнено», а не реальную дату."""
        if value in (None, "", DOTNET_EMPTY_DATE):
            return None
        return value

    @property
    def remaining(self) -> int:
        """Сколько ещё осталось принять. Отрицательное значение означает излишек."""
        return self.quantity - self.quantity_fact

    @property
    def is_done(self) -> bool:
        """Позиция больше не требует работы кладовщика.

        ВНИМАНИЕ, здесь есть предположение: статус 5 («Отсутствует») отнесён
        к НЕзавершённым. Обоснования в коде десктоп-версии не нашлось —
        возможно, отсутствующая позиция тоже считается закрытой.
        Уточнить у кладовщиков; см. открытые вопросы в записной книжке.
        """
        return self.status_position in (
            PositionStatus.ACCEPTED,
            PositionStatus.ACCEPTED_WITH_ISSUES,
            PositionStatus.EXCESS,
        )


FIELD_MAP = {
    "article": "article",
    "articleNew": "article_new",
    "manufacturer": "manufacturer",
    "name": "name",
    "quantity": "quantity",
    "quantityFact": "quantity_fact",
    "quantityScanned": "quantity_scanned",
    "quantityTotalScanned": "quantity_total_scanned",
    "price": "price",
    "priceTotal": "price_total",
    "refStutzen": "ref_stutzen",
    "refProvider": "ref_provider",
    "tradePoint": "trade_point",
    "numberCustomer": "number_customer",
    "statusPosition": "status_position",
    "comment": "comment",
    "processingStartTime": "processing_started_at",
    "processingCompletionTime": "processing_finished_at",
    "timeOfLastChange": "changed_at",
    # dcc_id намеренно не переносим: в ответе позиции он равен 0 и бесполезен
    # (значение, по которому позиции запрашивались, остаётся у вызывающего кода).
}


def parse_positions(payload: list[dict]) -> list[TaskPosition]:
    """Превращает сырой ответ API в список моделей.

    Битые строки пропускаются, а не роняют весь список: экран кладовщика
    должен показать остальные позиции задания, даже если одна запись аномальна.
    """
    positions: list[TaskPosition] = []
    for row in payload:
        try:
            positions.append(TaskPosition(**_to_snake(row)))
        except Exception:
            continue
    return positions


def _to_snake(row: dict) -> dict:
    return {FIELD_MAP[k]: v for k, v in row.items() if k in FIELD_MAP}
