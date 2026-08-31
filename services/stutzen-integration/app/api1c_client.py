"""
Клиент к api1c (catalog.stutzen.ru) — неофициальному расширению, написанному
разработчиком RoboStorages (не TradeSoft/Stutzen core team, см. docs/RoboStorages_scope_MVP.md).

Используется как fallback/для функциональности, которой нет в официальном TradeSoft
REST API v1 (в первую очередь — RoboStorage/GetStockTasks, RoboStorage/GetStockTaskPositions,
RoboStorage/CreateStockTask — для этого в TradeSoft REST API v1 аналога не нашлось).

Для смены статуса позиции предпочитайте tradesoft_client.set_position_status —
он официальный и документированный. api1c/Warehouse/PositionsSetStatuses здесь оставлен
как запасной путь на случай, если официальный API окажется недостаточным на практике
(см. TODO в routers/statuses.py).
"""
import os
import httpx

BASE_URL = os.environ["API1C_BASE_URL"]  # https://www.catalog.stutzen.ru/api1c
API_KEY = os.environ["API1C_API_KEY"]


class Api1cClient:
    def __init__(self):
        self._http = httpx.Client(
            base_url=BASE_URL, timeout=10.0, headers={"ApiKey": API_KEY}
        )

    def get_stock_tasks(self, **filters) -> dict:
        resp = self._http.get("/RoboStorage/GetStockTasks", params=filters)
        resp.raise_for_status()
        return resp.json()

    def get_stock_task_positions(self, stock_task_id: int) -> dict:
        resp = self._http.get(
            "/RoboStorage/GetStockTaskPositions", params={"stk_id": stock_task_id}
        )
        resp.raise_for_status()
        return resp.json()

    def get_order_states(self) -> dict:
        """Справочник статусов с человекочитаемыми названиями — заменяет
        захардкоженный в desktop-версии список из 93 значений (раздел 11 анализа)."""
        resp = self._http.get("/Warehouse/GetOrderStates")
        resp.raise_for_status()
        return resp.json()

    def set_positions_statuses(self, transitions: list[dict]) -> dict:
        """TODO: уточнить формат тела запроса у Stutzen — в документации был только
        пример ответа (itsOk, pst_id/pst_state_id/pst_state_id_new), не запроса.
        До уточнения не использовать в проде."""
        resp = self._http.post("/Warehouse/PositionsSetStatuses", json=transitions)
        resp.raise_for_status()
        return resp.json()
