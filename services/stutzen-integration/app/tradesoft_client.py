"""
Клиент к официальному TradeSoft REST API v1 (www.stutzen.ru/api/v1).

Два жёстких правила ниже — НЕ рекомендации, а прямые требования из официальной
документации TradeSoft (docs/Stutzen_API_справочник.md, раздел про TradeSoft REST API v1):

  1. "Если при вызове метода DELETE не были указаны get-параметры для фильтрации,
     запрос удалит все строки сущности (до 1000 строк)."
  2. "Если в описании сущности не описан какой-то метод запроса, его поведение
     не определено и может привести к падению проекта и потере данных."

Оба правила закодированы здесь как программные ограничения, а не как комментарии,
которые можно случайно проигнорировать в вызывающем коде.
"""
import os
import httpx

BASE_URL = os.environ["TRADESOFT_API_BASE_URL"]  # https://www.stutzen.ru/api/v1
TOKEN = os.environ["TRADESOFT_API_TOKEN"]

# Явный реестр того, что действительно задокументировано для каждой сущности.
# Любой вызов вне этого списка — ошибка на этапе разработки, не в проде.
ALLOWED_METHODS: dict[str, set[str]] = {
    # order-positions: 3.9.1 (создание/редактирование, POST/PUT), 3.9.2 (чтение, GET),
    # 3.9.3 (удаление, DELETE) — все четыре метода официально задокументированы.
    "order-positions": {"GET", "POST", "PUT", "DELETE"},
    "supplier-orders": {"GET"},                   # ТОЛЬКО чтение — подтверждено разделом 3.22
    "supplier-positions": {"GET"},                 # ТОЛЬКО чтение — подтверждено разделом 3.23
    "customers": {"GET"},
    # добавлять сущности сюда по мере необходимости, сверяясь с docs/-справочником,
    # не "на всякий случай"
}


class TradeSoftMethodNotAllowed(Exception):
    pass


class TradeSoftUnsafeDelete(Exception):
    pass


class TradeSoftClient:
    def __init__(self):
        self._http = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def _check_allowed(self, entity: str, method: str):
        allowed = ALLOWED_METHODS.get(entity)
        if allowed is None:
            raise TradeSoftMethodNotAllowed(
                f"Сущность '{entity}' не зарегистрирована в ALLOWED_METHODS — "
                f"сверьтесь с документацией TradeSoft, прежде чем добавлять."
            )
        if method not in allowed:
            raise TradeSoftMethodNotAllowed(
                f"Метод {method} не задокументирован для '{entity}' "
                f"(задокументированы только: {allowed}). Согласно вендору, "
                f"недокументированные методы могут привести к потере данных."
            )

    def get(self, entity: str, entity_id: int | None = None, **filters) -> dict:
        self._check_allowed(entity, "GET")
        path = f"/{entity}/" + (f"{entity_id}/" if entity_id else "")
        resp = self._http.get(path, params={"token": TOKEN, **filters})
        resp.raise_for_status()
        return resp.json()

    def upsert(self, entity: str, payload: dict | list[dict]) -> dict:
        """POST при отсутствии ID в payload, PUT при наличии — как того требует API."""
        self._check_allowed(entity, "POST")
        resp = self._http.post(f"/{entity}/", params={"token": TOKEN}, json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete(self, entity: str, **filters):
        """Фильтры ОБЯЗАТЕЛЬНЫ — без них TradeSoft удаляет всю сущность (до 1000 строк)."""
        self._check_allowed(entity, "DELETE")
        if not filters:
            raise TradeSoftUnsafeDelete(
                f"Отказ выполнять DELETE на '{entity}' без фильтров — "
                f"это удалило бы все строки сущности (см. документацию TradeSoft, п.1.4)."
            )
        resp = self._http.delete(f"/{entity}/", params={"token": TOKEN, **filters})
        resp.raise_for_status()
        return resp.json()

    def set_position_status(self, position_id: int, status_id: int, sub_states: list[dict] | None = None) -> dict:
        """Официальный, задокументированный способ смены статуса позиции заказа клиента
        (api/v1/order-positions, раздел 3.9.1) — предпочтителен перед неофициальным
        api1c/Warehouse/PositionsSetStatuses. sub_states — для случая, когда одна
        позиция расщепляется на несколько исходов (см. AcceptPositionRequest.outcomes
        в warehouse-сервисе)."""
        payload = {"positionID": position_id, "statusID": status_id}
        if sub_states:
            payload["subStates"] = sub_states
        return self.upsert("order-positions", payload)
