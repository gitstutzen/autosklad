"""
Клиент к официальному TradeSoft REST API v1 (www.stutzen.ru/api/v1).

ЧЕТЫРЕ уровня защиты, все — программные, а не "договорённости в README":

  1. Режим только чтения (по умолчанию ВКЛЮЧЁН). У проекта нет тестового контура —
     работаем против боевого Stutzen, поэтому запись требует явного разрешения.
     См. libs/common/read_only.py.

  2. Белый список задокументированных методов. Вендор прямо предупреждает:
     "если в описании сущности не описан какой-то метод запроса, его поведение
     не определено и может привести к падению проекта и потере данных".

  3. Запрет DELETE без фильтров. Вендор: "если при вызове DELETE не были указаны
     get-параметры для фильтрации, запрос удалит все строки сущности (до 1000)".

  4. Журнал всех обращений с маскировкой секретов. Токен передаётся GET-параметром,
     поэтому без маскировки он попадал бы в каждую строчку лога.
"""
import os
import httpx

from libs.common.read_only import ensure_writes_allowed, is_read_only
from libs.common.outbound_log import log_outbound, redact_mapping

BASE_URL = os.environ["TRADESOFT_API_BASE_URL"]  # https://www.stutzen.ru/api/v1
TOKEN = os.environ["TRADESOFT_API_TOKEN"]

# Явный реестр того, что действительно задокументировано для каждой сущности.
# Пополнять только со сверкой по docs/Stutzen_API_справочник.md, не "на всякий случай".
ALLOWED_METHODS: dict[str, set[str]] = {
    # order-positions: 3.9.1 (POST/PUT), 3.9.2 (GET), 3.9.3 (DELETE) — все задокументированы
    "order-positions": {"GET", "POST", "PUT", "DELETE"},
    "supplier-orders": {"GET"},        # ТОЛЬКО чтение — подтверждено разделом 3.22
    "supplier-positions": {"GET"},     # ТОЛЬКО чтение — подтверждено разделом 3.23
    "customers": {"GET"},
}

WRITE_METHODS = {"POST", "PUT", "DELETE"}


class TradeSoftMethodNotAllowed(Exception):
    pass


class TradeSoftUnsafeDelete(Exception):
    pass


class TradeSoftClient:
    def __init__(self):
        self._http = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # ---- защитные проверки ----

    def _check_allowed(self, entity: str, method: str) -> None:
        allowed = ALLOWED_METHODS.get(entity)
        if allowed is None:
            raise TradeSoftMethodNotAllowed(
                f"Сущность '{entity}' не зарегистрирована в ALLOWED_METHODS — "
                f"сверьтесь с документацией TradeSoft, прежде чем добавлять."
            )
        if method not in allowed:
            raise TradeSoftMethodNotAllowed(
                f"Метод {method} не задокументирован для '{entity}' "
                f"(задокументированы только: {sorted(allowed)}). Согласно вендору, "
                f"недокументированные методы могут привести к потере данных."
            )

    def _guard(self, entity: str, method: str) -> None:
        """Единая точка проверки перед любым запросом: сначала белый список,
        затем — для записывающих методов — режим только чтения."""
        self._check_allowed(entity, method)
        if method in WRITE_METHODS:
            ensure_writes_allowed(f"{method} {entity}")

    # ---- операции ----

    def get(self, entity: str, entity_id: int | None = None, **filters) -> dict:
        self._guard(entity, "GET")
        path = f"/{entity}/" + (f"{entity_id}/" if entity_id else "")
        with log_outbound(
            "tradesoft", f"GET {entity}", f"{BASE_URL}{path}",
            read_only=is_read_only(), filters=redact_mapping(filters),
        ):
            resp = self._http.get(path, params={"token": TOKEN, **filters})
            resp.raise_for_status()
            return resp.json()

    def upsert(self, entity: str, payload: dict | list[dict]) -> dict:
        """Создание/обновление. Блокируется в режиме только чтения."""
        self._guard(entity, "POST")
        with log_outbound(
            "tradesoft", f"POST {entity}", f"{BASE_URL}/{entity}/",
            read_only=is_read_only(), payload=redact_mapping(
                payload if isinstance(payload, dict) else {"items": len(payload)}
            ),
        ):
            resp = self._http.post(f"/{entity}/", params={"token": TOKEN}, json=payload)
            resp.raise_for_status()
            return resp.json()

    def delete(self, entity: str, **filters):
        """Фильтры ОБЯЗАТЕЛЬНЫ — без них TradeSoft удаляет всю сущность (до 1000 строк).
        Проверка фильтров идёт ДО режима только чтения, чтобы небезопасный вызов
        был виден как ошибка даже там, где запись разрешена."""
        self._check_allowed(entity, "DELETE")
        if not filters:
            raise TradeSoftUnsafeDelete(
                f"Отказ выполнять DELETE на '{entity}' без фильтров — "
                f"это удалило бы все строки сущности (документация TradeSoft, п.1.4)."
            )
        ensure_writes_allowed(f"DELETE {entity}")
        with log_outbound(
            "tradesoft", f"DELETE {entity}", f"{BASE_URL}/{entity}/",
            read_only=is_read_only(), filters=redact_mapping(filters),
        ):
            resp = self._http.delete(f"/{entity}/", params={"token": TOKEN, **filters})
            resp.raise_for_status()
            return resp.json()

    def set_position_status(
        self, position_id: int, status_id: int, sub_states: list[dict] | None = None
    ) -> dict:
        """Официальный способ смены статуса позиции заказа клиента
        (api/v1/order-positions, раздел 3.9.1). sub_states — для случая, когда одна
        позиция расщепляется на несколько исходов (принято / брак / недостача).

        ВНИМАНИЕ: это запись в боевой Stutzen. Заблокирована, пока не снят
        режим только чтения."""
        payload: dict = {"positionID": position_id, "statusID": status_id}
        if sub_states:
            payload["subStates"] = sub_states
        return self.upsert("order-positions", payload)
