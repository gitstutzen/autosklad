"""
Клиент к api1c (catalog.stutzen.ru) — неофициальному расширению, написанному
разработчиком RoboStorages (не командой TradeSoft, см. docs/RoboStorages_scope_MVP.md).

Используется для того, чего нет в официальном TradeSoft REST API v1: получение
складских заданий и их позиций (RoboStorage/GetStockTasks, GetStockTaskPositions),
справочник статусов.

Для смены статуса позиции предпочитайте tradesoft_client.set_position_status —
он официальный и задокументированный.

Защиты те же, что и в клиенте TradeSoft: режим только чтения по умолчанию
(нет тестового контура, работаем против боевого Stutzen) и журнал вызовов
с маскировкой ключа. Ключ здесь передаётся заголовком ApiKey, а не в URL,
но в лог он всё равно не попадает.
"""
import os
import httpx

from libs.common.read_only import ensure_writes_allowed, is_read_only
from libs.common.outbound_log import log_outbound, redact_mapping

BASE_URL = os.environ["API1C_BASE_URL"]  # https://www.catalog.stutzen.ru/api1c
API_KEY = os.environ["API1C_API_KEY"]

# Обычные запросы отвечают за доли секунды, десяти секунд хватает с запасом.
DEFAULT_TIMEOUT = float(os.environ.get("API1C_TIMEOUT", "10"))

# Полная выгрузка — отдельная история: 452 000 записей, 186 МБ, около 40 секунд
# только на передачу. С обычным таймаутом она не успевает в принципе
# (проверено 02.09.2026: ReadTimeout ровно на десятой секунде).
# Ставим с большим запасом: объём данных растёт, а обрыв на 39-й секунде
# означает выброшенные 180 МБ трафика и повторную попытку с нуля.
FULL_DUMP_TIMEOUT = float(os.environ.get("API1C_FULL_DUMP_TIMEOUT", "300"))



def is_full_dump_request(filters: dict) -> bool:
    """Запрос без count означает выгрузку всей истории заданий."""
    return "count" not in filters


def timeout_for(filters: dict) -> float:
    """Сколько ждать ответа. Вынесено отдельно, чтобы решение было проверяемым:
    именно здесь была ошибка, из-за которой полная синхронизация не работала."""
    return FULL_DUMP_TIMEOUT if is_full_dump_request(filters) else DEFAULT_TIMEOUT


class Api1cClient:
    def __init__(self):
        self._http = httpx.Client(
            base_url=BASE_URL, timeout=DEFAULT_TIMEOUT, headers={"ApiKey": API_KEY}
        )

    # ---- чтение ----

    def get_stock_tasks(self, **filters) -> dict:
        """Список складских заданий (приходов). Только чтение — безопасно.

        Без параметра count api1c отдаёт ВСЮ историю: 452 000 записей, 186 МБ,
        около 40 секунд только на передачу. Для такого запроса берём отдельный
        длинный таймаут — с обычным десятисекундным он обрывается, не успевая
        даже дочитать ответ (проверено 02.09.2026: ReadTimeout ровно на 10-й сек).
        """
        is_full_dump = is_full_dump_request(filters)
        timeout = timeout_for(filters)
        operation = "GetStockTasks (полная выгрузка)" if is_full_dump else "GetStockTasks"

        with log_outbound(
            "api1c", operation, f"{BASE_URL}/RoboStorage/GetStockTasks",
            read_only=is_read_only(), filters=redact_mapping(filters),
        ):
            resp = self._http.get(
                "/RoboStorage/GetStockTasks", params=filters, timeout=timeout
            )
            resp.raise_for_status()
            return resp.json()

    def get_stock_task_positions(self, document_number: int) -> dict:
        """Позиции конкретного задания.

        ВНИМАНИЕ на параметр: метод ждёт `dcc_id`, и туда идёт **documentNumber**
        задания, а не его `id` и не `stk_id` (в задании `stk_id` всегда 0).
        Проверено пробником 02.09.2026 перебором 7 имён × 3 значений.
        Подтверждается SQL десктоп-версии:
            PositionsStorage.dcc_id = StockTasks.DocumentNumber

        Здесь параметр назван document_number специально — чтобы вызывающий код
        не мог по ошибке передать id задания, не заметив подмены. При неверном
        значении API отвечает 200 OK и пустым списком, без всякой ошибки.
        """
        with log_outbound(
            "api1c", "GetStockTaskPositions",
            f"{BASE_URL}/RoboStorage/GetStockTaskPositions",
            read_only=is_read_only(), dcc_id=document_number,
        ):
            resp = self._http.get(
                "/RoboStorage/GetStockTaskPositions", params={"dcc_id": document_number}
            )
            resp.raise_for_status()
            return resp.json()

    def get_order_states(self) -> dict:
        """Справочник статусов с человекочитаемыми названиями — заменяет
        захардкоженный в desktop-версии список из 93 значений (раздел 11 анализа)."""
        with log_outbound(
            "api1c", "GetOrderStates", f"{BASE_URL}/Warehouse/GetOrderStates",
            read_only=is_read_only(),
        ):
            resp = self._http.get("/Warehouse/GetOrderStates")
            resp.raise_for_status()
            return resp.json()

    # ---- запись ----

    def set_positions_statuses(self, transitions: list[dict]) -> dict:
        """ЗАПИСЬ в боевой Stutzen — массовая смена статусов позиций.

        Заблокирована, пока включён режим только чтения.

        TODO: формат тела запроса не подтверждён — в документации был только пример
        ответа (itsOk, pst_id/pst_state_id/pst_state_id_new), не запроса.
        До уточнения у Stutzen не использовать даже при снятом read-only."""
        ensure_writes_allowed("PositionsSetStatuses (api1c)")
        with log_outbound(
            "api1c", "PositionsSetStatuses",
            f"{BASE_URL}/Warehouse/PositionsSetStatuses",
            read_only=is_read_only(), transitions_count=len(transitions),
        ):
            resp = self._http.post("/Warehouse/PositionsSetStatuses", json=transitions)
            resp.raise_for_status()
            return resp.json()
