"""
Тесты таймаутов клиента api1c.

Полная выгрузка заданий идёт около 40 секунд (452 000 записей, 186 МБ).
С обычным десятисекундным таймаутом она обрывается, не успевая дочитать ответ —
именно это произошло 02.09.2026 при первом запуске полной синхронизации.

Ошибка была неочевидной: инкрементальная синхронизация при этом работала
нормально, потому что укладывалась в лимит. То есть сломан был только один
режим из двух, и заметить это можно было лишь запустив тяжёлый.
"""
from app import api1c_client
from app.api1c_client import is_full_dump_request, timeout_for


def test_request_without_count_is_full_dump():
    """Отсутствие count означает выгрузку всей истории — 186 МБ."""
    assert is_full_dump_request({}) is True


def test_request_with_count_is_not_full_dump():
    assert is_full_dump_request({"count": 5000}) is False
    assert is_full_dump_request({"count": 1}) is False


def test_full_dump_gets_long_timeout():
    assert timeout_for({}) == api1c_client.FULL_DUMP_TIMEOUT


def test_incremental_gets_default_timeout():
    """Запрос с count отдаётся за доли секунды. Длинный таймаут ему не нужен:
    если сервер завис, лучше узнать об этом быстро, а не ждать пять минут."""
    assert timeout_for({"count": 5000}) == api1c_client.DEFAULT_TIMEOUT


def test_full_dump_timeout_is_long_enough():
    """Полная выгрузка идёт около 40 секунд. Запас нужен: объём данных растёт,
    а обрыв означает выброшенные 186 МБ трафика и повтор с нуля."""
    assert api1c_client.FULL_DUMP_TIMEOUT >= 120, (
        "таймаут полной выгрузки слишком короткий — она занимает ~40 секунд "
        "и со временем будет только дольше"
    )


def test_default_timeout_stays_short():
    """Обычные запросы не должны висеть минутами: быстрый отказ лучше,
    чем зависший экран у кладовщика."""
    assert api1c_client.DEFAULT_TIMEOUT <= 30


def test_timeouts_differ():
    """Если оба таймаута совпали, значит разделение потерялось при правках."""
    assert api1c_client.FULL_DUMP_TIMEOUT > api1c_client.DEFAULT_TIMEOUT
