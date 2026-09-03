"""
Тесты режима "только чтение".

Почему это важно именно здесь: у проекта нет тестового контура Stutzen —
разработка идёт против боевого API. Эти тесты проверяют, что защита от
случайной записи в боевые данные действительно работает, а не только описана.
"""
import os
import pytest

os.environ.setdefault("TRADESOFT_API_BASE_URL", "https://example.invalid/api/v1")
os.environ.setdefault("TRADESOFT_API_TOKEN", "test-token")

from libs.common.read_only import (
    is_read_only,
    ensure_writes_allowed,
    WriteBlockedByReadOnlyMode,
)
from libs.common.outbound_log import redact_url, redact_mapping


# ---- сам режим ----

def test_read_only_is_on_by_default(monkeypatch):
    """Главная проверка: если переменная не задана (потерялась при деплое,
    опечатана, поднялось не то окружение) — запись ЗАПРЕЩЕНА.
    Ошибка должна быть в безопасную сторону."""
    monkeypatch.delenv("STUTZEN_READ_ONLY", raising=False)
    assert is_read_only() is True


def test_read_only_stays_on_for_any_value_except_false(monkeypatch):
    """Опечатка в значении не должна случайно открывать запись."""
    for value in ["true", "TRUE", "1", "yes", "", "no", "falsee", "off"]:
        monkeypatch.setenv("STUTZEN_READ_ONLY", value)
        assert is_read_only() is True, f"значение {value!r} не должно снимать защиту"


def test_writes_allowed_only_with_explicit_false(monkeypatch):
    monkeypatch.setenv("STUTZEN_READ_ONLY", "false")
    assert is_read_only() is False
    ensure_writes_allowed("тестовая операция")  # не должно бросить


def test_write_blocked_in_read_only_mode(monkeypatch):
    monkeypatch.setenv("STUTZEN_READ_ONLY", "true")
    with pytest.raises(WriteBlockedByReadOnlyMode):
        ensure_writes_allowed("смена статуса позиции")


# ---- защита клиента TradeSoft ----

def test_client_blocks_status_write_in_read_only(monkeypatch):
    """Смена статуса реального заказа не должна уходить в сеть,
    пока включён режим только чтения."""
    monkeypatch.setenv("STUTZEN_READ_ONLY", "true")
    from app.tradesoft_client import TradeSoftClient

    client = TradeSoftClient()
    with pytest.raises(WriteBlockedByReadOnlyMode):
        client.set_position_status(position_id=123, status_id=45)


def test_client_allows_reads_in_read_only(monkeypatch):
    """Чтение в режиме только чтения разрешено — иначе разрабатывать было бы нельзя.
    Сетевая ошибка на несуществующий хост здесь ожидаема и означает,
    что защита пропустила вызов дальше."""
    monkeypatch.setenv("STUTZEN_READ_ONLY", "true")
    from app.tradesoft_client import TradeSoftClient

    client = TradeSoftClient()
    try:
        client.get("supplier-orders", orderID=1)
    except WriteBlockedByReadOnlyMode:
        pytest.fail("чтение не должно блокироваться режимом только чтения")
    except Exception:
        pass  # сетевая ошибка — нормально


# ---- маскировка секретов в логах ----

def test_token_is_redacted_from_url():
    url = "https://www.stutzen.ru/api/v1/order-positions/?token=SECRET123&orderID=5"
    result = redact_url(url)
    assert "SECRET123" not in result
    assert "orderID=5" in result  # полезная часть остаётся читаемой


def test_apikey_is_redacted_from_url():
    url = "https://www.catalog.stutzen.ru/api1c/RoboStorage/GetStockTasks?apikey=abc-123"
    assert "abc-123" not in redact_url(url)


def test_secret_keys_redacted_from_mapping():
    data = {"token": "SECRET", "ApiKey": "SECRET2", "orderID": 7}
    result = redact_mapping(data)
    assert result["token"] == "***"
    assert result["ApiKey"] == "***"
    assert result["orderID"] == 7
