"""
Тест на защитные правила TradeSoftClient (app/tradesoft_client.py) — тоже реально
готовый код, не заглушка. Проверяет, что запрещённые по документации TradeSoft
действия (раздел "Технические детали TradeSoft REST API v1" в docs/) отклоняются
ДО сетевого запроса, а не полагаются на дисциплину того, кто вызывает клиента.
Не требует сети — исключение выбрасывается раньше, чем клиент успевает
что-либо отправить.
"""
import os
import pytest

os.environ.setdefault("TRADESOFT_API_BASE_URL", "https://example.invalid/api/v1")
os.environ.setdefault("TRADESOFT_API_TOKEN", "test-token")

from app.tradesoft_client import TradeSoftClient, TradeSoftMethodNotAllowed, TradeSoftUnsafeDelete


def test_delete_without_filters_is_rejected():
    client = TradeSoftClient()
    with pytest.raises(TradeSoftUnsafeDelete):
        client.delete("order-positions")  # без фильтров — удалило бы всё


def test_delete_with_filter_passes_the_guard():
    """Проверяем, что guard пропускает вызов дальше (до сети), когда фильтр указан —
    сам факт сетевого похода здесь не проверяем, это дело интеграционных тестов."""
    client = TradeSoftClient()
    try:
        client.delete("order-positions", positionID=123)
    except TradeSoftUnsafeDelete:
        pytest.fail("guard не должен был сработать — фильтр указан")
    except Exception:
        pass  # сетевая ошибка на невалидный хост — это ожидаемо и нормально в этом тесте


def test_write_to_get_only_entity_is_rejected():
    """supplier-orders задокументирован в TradeSoft только на GET (раздел 3.22
    документации) — попытка записи должна быть отклонена на уровне кода."""
    client = TradeSoftClient()
    with pytest.raises(TradeSoftMethodNotAllowed):
        client.upsert("supplier-orders", {"id": 1})


def test_unregistered_entity_is_rejected():
    """Сущность, которой нет в ALLOWED_METHODS вообще — тоже отказ, а не 'а вдруг сработает'."""
    client = TradeSoftClient()
    with pytest.raises(TradeSoftMethodNotAllowed):
        client.get("some-entity-nobody-checked-yet")
