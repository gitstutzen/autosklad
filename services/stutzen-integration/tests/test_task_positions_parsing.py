"""
Тесты разбора позиций задания.

Образец взят из реального ответа боевого API (пробник от 02.09.2026),
артикул и наименование заменены на условные.
"""
from datetime import datetime

from app.task_positions import parse_positions, TaskPosition, PositionStatus


def make_row(**overrides) -> dict:
    """Строка в формате, который реально отдаёт api1c."""
    row = {
        "dcc_id": 0,
        "article": "ABC1117",
        "articleNew": "",
        "manufacturer": "ПРОИЗВОДИТЕЛЬ",
        "name": "Трос стояночного тормоза",
        "quantity": 1,
        "quantityFact": 0,
        "quantityScanned": 0,
        "quantityTotalScanned": 0,
        "price": 515.48,
        "priceTotal": 515.48,
        "refStutzen": 14664960,
        "refProvider": 14667317,
        "tradePoint": 12,
        "numberCustomer": 262607,
        "comment": None,
        "processingStartTime": "0001-01-01T00:00:00",
        "processingCompletionTime": "0001-01-01T00:00:00",
        "timeOfLastChange": "2026-09-02T02:47:34.587",
        "statusPosition": 1,
    }
    row.update(overrides)
    return row


def test_parses_position():
    positions = parse_positions([make_row()])
    assert len(positions) == 1
    assert isinstance(positions[0], TaskPosition)


def test_maps_fields():
    p = parse_positions([make_row()])[0]
    assert p.article == "ABC1117"
    assert p.quantity == 1
    assert p.quantity_fact == 0
    assert p.price == 515.48
    assert p.ref_stutzen == 14664960
    assert p.trade_point == 12
    assert p.number_customer == 262607
    assert p.status_position == PositionStatus.UNPROCESSED


def test_empty_dotnet_dates_become_none():
    """0001-01-01 означает «обработка не начиналась», а не дату из первого века."""
    p = parse_positions([make_row()])[0]
    assert p.processing_started_at is None
    assert p.processing_finished_at is None


def test_real_date_is_parsed():
    p = parse_positions([make_row()])[0]
    assert p.changed_at == datetime(2026, 9, 2, 2, 47, 34, 587000)


def test_remaining_quantity():
    p = parse_positions([make_row(quantity=10, quantityFact=4)])[0]
    assert p.remaining == 6


def test_remaining_is_negative_on_excess():
    """Излишек: приняли больше, чем ожидалось."""
    p = parse_positions([make_row(quantity=10, quantityFact=12)])[0]
    assert p.remaining == -2


def test_is_done_for_accepted_statuses():
    for status in (3, 4, 6):
        p = parse_positions([make_row(statusPosition=status)])[0]
        assert p.is_done, f"статус {status} должен считаться обработанным"


def test_is_not_done_for_open_statuses():
    for status in (1, 2, 5):
        p = parse_positions([make_row(statusPosition=status)])[0]
        assert not p.is_done, f"статус {status} не должен считаться обработанным"


def test_bad_row_is_skipped():
    rows = [make_row(), {"article": None, "quantity": "не число"}, make_row()]
    assert len(parse_positions(rows)) == 2


def test_empty_response():
    assert parse_positions([]) == []


def test_unknown_fields_ignored():
    """API может добавить поля — это не должно ничего ломать."""
    assert len(parse_positions([make_row(someNewField="значение")])) == 1
